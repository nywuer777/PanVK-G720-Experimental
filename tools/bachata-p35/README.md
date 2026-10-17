# P35 — Minecraft shader image overlap diagnostic

Source-only. Public pinned commit `be6bc2e9c60799e071dd2fafa6216e8d80ec619c`. P35 implements privacy-safe, opt-in diagnostic in active `Rasterizer::BindTextures()` using `Shader::ImageResource::is_atomic`, storage access and dynamic mip flags. Logs exclude guest addresses and data. Source SHA-256 `8135c79a0665921ddbf411b473a267dd911825a983778a9e4025ca2eebe7b3a4`. Does not change Vulkan descriptors or shader semantics; Minecraft and Outlast not certified fixed, P23 functional APK untouched.
