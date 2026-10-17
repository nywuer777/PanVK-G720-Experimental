#!/usr/bin/env python3
"""Read-only, bounded APK Signature Scheme v2 checker and public signer fingerprint.

Requires cryptography. Validates the cryptographic signature, certificate/SPKI
binding, and Android's v2 whole-file content digest. Does NOT validate the
original maintainer's identity, installed UID, or a live SAF broker session.
"""
from __future__ import annotations
import argparse, hashlib, json, struct
from pathlib import Path
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, dsa, padding

MAX_SIGNING_BLOCK=16*1024*1024
MAX_NESTED=8*1024*1024
CHUNK=1024*1024
APK_SIG_MAGIC=b'APK Sig Block 42'
ID_V2=0x7109871a
# Android v2 signature algorithm numeric IDs: family, digest, padding.
ALGORITHMS={
    0x0101: ('rsa_pss', 'sha256'), 0x0102: ('rsa_pss','sha512'),
    0x0103: ('rsa_pkcs1','sha256'), 0x0104: ('rsa_pkcs1','sha512'),
    0x0201: ('ecdsa','sha256'), 0x0202: ('ecdsa','sha512'),
    0x0301: ('dsa','sha256'),
}
class SignatureError(ValueError): pass

def require(pred, message):
    if not pred:raise SignatureError(message)

class Reader:
    def __init__(self, buf):
        require(isinstance(buf,(bytes,bytearray,memoryview)) and len(buf)<=MAX_NESTED,'FIELD_TOO_LARGE')
        self.buf=memoryview(buf);self.pos=0
    def int(self):
        require(self.pos+4<=len(self.buf),'TRUNCATED_INTEGER')
        value=struct.unpack_from('<I',self.buf,self.pos)[0];self.pos+=4
        return value
    def blob(self):
        size=self.int(); require(size<=MAX_NESTED and size<=len(self.buf)-self.pos,'TRUNCATED_BLOB')
        b=self.buf[self.pos:self.pos+size].tobytes();self.pos+=size
        return b
    def finish(self): require(self.pos==len(self.buf),'TRAILING_SIGNED_DATA')

def entries(encoded):
    r=Reader(encoded);out=[]
    while r.pos<len(r.buf):
        out.append(Reader(r.blob()))
    return out

def find_eocd(f,size):
    n=min(size,65557); f.seek(size-n); tail=f.read(n)
    require(len(tail)>=22,'NO_EOCD')
    for p in range(len(tail)-22,-1,-1):
        if tail[p:p+4]!=b'PK\x05\x06':continue
        comment=struct.unpack_from('<H',tail,p+20)[0]
        if p+22+comment!=len(tail):continue
        disk,cd_disk,entries_disk,total_entries,cd_size,cd_offset=struct.unpack_from('<HHHHII',tail,p+4)
        require(disk==0 and cd_disk==0 and entries_disk==total_entries,'MULTIDISK_UNSUPPORTED')
        require(cd_size!=0xffffffff and cd_offset!=0xffffffff,'ZIP64_UNSUPPORTED')
        eocd_start=size-n+p
        require(cd_offset+cd_size==eocd_start and cd_offset<=size,'CENTRAL_DIRECTORY_BOUNDS')
        return eocd_start,cd_offset,tail[p:]
    raise SignatureError('EOCD_NOT_FOUND')

def apk_signing_block(f,cd_offset):
    require(cd_offset>=32,'MISSING_SIGNING_BLOCK')
    f.seek(cd_offset-24);footer=f.read(24)
    require(len(footer)==24 and footer[8:]==APK_SIG_MAGIC,'APK_SIGNATURE_BLOCK_NOT_FOUND')
    n=struct.unpack_from('<Q',footer)[0]
    require(24<=n<=MAX_SIGNING_BLOCK,'APK_SIGNING_BLOCK_BOUNDS')
    start=cd_offset-n-8
    require(start>=0,'APK_SIGNING_BLOCK_START_INVALID')
    f.seek(start); head=f.read(8)
    require(len(head)==8 and struct.unpack('<Q',head)[0]==n,'APK_SIGNING_BLOCK_LENGTH_MISMATCH')
    pairs={}; pos=start+8
    while pos<cd_offset-24:
        require(pos+12<=cd_offset-24,'APK_SIGNING_BLOCK_PAIR_TRUNCATED')
        f.seek(pos); row=f.read(12)
        length,typ=struct.unpack('<QI',row)
        require(4<=length<=MAX_SIGNING_BLOCK and pos+8+length<=cd_offset-24,'APK_SIGNING_PAIR_BOUNDS')
        require(typ not in pairs,'DUPLICATE_SIGNING_PAIR_ID')
        require(length-4<=MAX_NESTED,'SIGNING_PAIR_TOO_LARGE')
        val=f.read(length-4)
        require(len(val)==length-4,'SIGNING_PAIR_TRUNCATED')
        pairs[typ]=val; pos+=8+length
    require(pos==cd_offset-24,'SIGNING_PAIR_BOUNDARY_ERROR')
    return start,pairs

def parse_signer(encoded):
    r=Reader(encoded); signed=r.blob(); signatures=r.blob(); spki=r.blob();r.finish()
    s=Reader(signed);digests=s.blob();certs=s.blob();s.blob();s.finish()
    dig={};sigs={}
    for record in entries(digests):
        aid=record.int();value=record.blob();record.finish()
        require(aid not in dig,'DUPLICATE_DIGEST_ALGORITHM');dig[aid]=value
    for record in entries(signatures):
        aid=record.int();value=record.blob();record.finish()
        require(aid not in sigs,'DUPLICATE_SIGNATURE_ALGORITHM');sigs[aid]=value
    cert_entries=entries(certs); require(cert_entries,'NO_SIGNER_CERTIFICATE')
    chain=[]
    for item in cert_entries:
        der=item.buf.tobytes();item.pos=len(item.buf)
        chain.append(x509.load_der_x509_certificate(der))
    pubkey=chain[0].public_key()
    require(pubkey.public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)==spki,'CERTIFICATE_PUBLIC_KEY_MISMATCH')
    compatible=[alg for alg in sigs if alg in ALGORITHMS and alg in dig]
    require(compatible,'NO_SUPPORTED_SIGNATURE_ALGORITHM')
    # Choose the strongest digest, then signature scheme. v2 supports algorithm lists.
    chosen=max(compatible,key=lambda a:(ALGORITHMS[a][1]=='sha512',a in (0x0101,0x0102),a))
    kind,hashname=ALGORITHMS[chosen];h=hashes.SHA512() if hashname=='sha512' else hashes.SHA256()
    try:
        if kind=='rsa_pss':
            require(isinstance(pubkey,rsa.RSAPublicKey),'PUBLIC_KEY_TYPE_MISMATCH')
            pubkey.verify(sigs[chosen],signed,padding.PSS(mgf=padding.MGF1(h),salt_length=h.digest_size),h)
        elif kind=='rsa_pkcs1':
            require(isinstance(pubkey,rsa.RSAPublicKey),'PUBLIC_KEY_TYPE_MISMATCH')
            pubkey.verify(sigs[chosen],signed,padding.PKCS1v15(),h)
        elif kind=='ecdsa':
            require(isinstance(pubkey,ec.EllipticCurvePublicKey),'PUBLIC_KEY_TYPE_MISMATCH')
            pubkey.verify(sigs[chosen],signed,ec.ECDSA(h))
        else:
            require(isinstance(pubkey,dsa.DSAPublicKey),'PUBLIC_KEY_TYPE_MISMATCH')
            pubkey.verify(sigs[chosen],signed,h)
    except InvalidSignature as e: raise SignatureError('APK_V2_SIGNATURE_INVALID') from e
    require(len(dig[chosen])==(64 if hashname=='sha512' else 32),'CONTENT_DIGEST_SIZE_INVALID')
    return {'algorithm_id':chosen,'digest_name':hashname,'content_digest':dig[chosen],
            'cert_sha256':hashlib.sha256(chain[0].public_bytes(serialization.Encoding.DER)).hexdigest(),
            'cert_count':len(chain),'signature_verified':True}

def stream_segments(f,segments):
    for offset,length in segments:
        require(offset>=0 and length>=0,'SEGMENT_BOUNDS')
        f.seek(offset)
        while length:
            part=f.read(min(CHUNK,length));require(part,'UNEXPECTED_EOF')
            yield part;length-=len(part)

def content_digest(f, sig_start, cd_offset, eocd_start, eocd_data, hashname):
    # Sections: data before signing block, central directory, EOCD with
    # central-directory offset rewritten to the signing block's start.
    require(sig_start<=cd_offset<=eocd_start,'CONTENT_SECTION_BOUNDS')
    adjusted=bytearray(eocd_data);struct.pack_into('<I',adjusted,16,sig_start)
    # Stream source sections without retaining APK content in memory.
    def parts():
        yield from stream_segments(f,[(0,sig_start),(cd_offset,eocd_start-cd_offset)])
        for pos in range(0,len(adjusted),CHUNK):yield adjusted[pos:pos+CHUNK]
    digests=[]
    for chunk in parts():
        digests.append(hashlib.new(hashname,b'\xa5'+struct.pack('<I',len(chunk))+chunk).digest())
    return hashlib.new(hashname,b'\x5a'+struct.pack('<I',len(digests))+b''.join(digests)).digest()

def verify_apk(path:Path, expected_sha256=None):
    require(path.is_file(),'APK_FILE_MISSING')
    size=path.stat().st_size
    require(22<size<4*1024**3,'APK_SIZE_UNSUPPORTED')
    h=hashlib.sha256()
    with path.open('rb') as f:
        for buf in iter(lambda:f.read(1024*1024),b''): h.update(buf)
        apk_sha=h.hexdigest()
        if expected_sha256 is not None:require(apk_sha==expected_sha256,'PINNED_APK_SHA256_MISMATCH')
        eocd,cd,tail=find_eocd(f,size)
        start,pairs=apk_signing_block(f,cd)
        require(ID_V2 in pairs,'APK_V2_BLOCK_MISSING')
        outer=Reader(pairs[ID_V2]); signers_blob=outer.blob(); outer.finish()
        signers=entries(signers_blob);require(1<=len(signers)<=10,'INVALID_SIGNER_COUNT')
        verified=[]
        for signer in signers:
            signer_bytes=signer.buf.tobytes();signer.pos=len(signer.buf)
            cert=parse_signer(signer_bytes)
            observed=content_digest(f,start,cd,eocd,tail,cert['digest_name'])
            require(observed==cert['content_digest'],'APK_V2_CONTENT_DIGEST_INVALID')
            verified.append(cert)
    return {'schema':'bachata-p15-apk-v2-identity-v1','apk_sha256':apk_sha,
            'v2_signature_verified':True,'v2_file_integrity_verified':True,
            'signers':[{'certificate_sha256':s['cert_sha256'],'algorithm_id':hex(s['algorithm_id']),
                        'certificate_chain_length':s['cert_count']} for s in verified],
            'signing_key_possession_verified':False,'maintainer_identity_verified':False,
            'installed_app_identity_verified':False,'live_saf_broker_verified':False}

def main():
    p=argparse.ArgumentParser(description='Offline APK v2 cryptographic identity, read-only')
    p.add_argument('--apk',type=Path,required=True)
    p.add_argument('--expected-sha256')
    p.add_argument('--compare',type=Path,help='Optional second APK whose signer(s) will be compared')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    require(not a.output.exists() and a.output.resolve() not in [a.apk.resolve(),*( [a.compare.resolve()] if a.compare else [])], 'UNSAFE_OUTPUT_PATH')
    r=verify_apk(a.apk,a.expected_sha256)
    if a.compare:
        other=verify_apk(a.compare)
        r['compared_candidate_sha256']=other['apk_sha256']
        r['signing_certificates_equal']=(set(s['certificate_sha256'] for s in r['signers'])==set(s['certificate_sha256'] for s in other['signers']))
        r['candidate_crypto_verified']=other['v2_signature_verified']
        # Cert equality alone is NOT proof of Android upgrade/downgrade compatibility.
        r['upgrade_compatibility_verified']=False
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf8') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
    print('P15_V2_SIGNATURE_AND_CONTENT_DIGEST_PASS')
if __name__=='__main__':main()
