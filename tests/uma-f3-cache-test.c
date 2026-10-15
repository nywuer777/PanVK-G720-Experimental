/* UMA F3 cache policy regression test, using Mesa's intrusive list. MIT */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include "util/list.h"

struct bo { struct list_head node; size_t size; bool active; };
struct cache { struct list_head free_bos; };

/* Mirror the driver F3 insertion logic with mocked BO capacities. */
static void insert_idle(struct cache *cache, struct bo *bo)
{
   assert(!bo->active);
   const size_t capacity = bo->size;
   list_for_each_entry(struct bo, cached, &cache->free_bos, node) {
      if (cached->size > capacity) {
         list_addtail(&bo->node, &cached->node);
         return;
      }
   }
   list_addtail(&bo->node, &cache->free_bos);
}

static struct bo *take_best_fit(struct cache *cache, size_t requested)
{
   list_for_each_entry(struct bo, bo, &cache->free_bos, node) {
      if (bo->size >= requested) {
         list_del(&bo->node);
         bo->active = true;
         return bo;
      }
   }
   return NULL;
}

static struct bo *evict_max(struct cache *cache)
{
   if (list_is_empty(&cache->free_bos))
      return NULL;
   struct bo *victim =
      list_last_entry(&cache->free_bos, struct bo, node);
   list_del(&victim->node);
   return victim;
}

static void sorted_and_idle(struct cache *cache)
{
   size_t prev = 0;
   list_for_each_entry(struct bo, bo, &cache->free_bos, node) {
      assert(!bo->active);
      assert(bo->size >= prev);
      prev = bo->size;
   }
}

int main(void)
{
   struct cache cache;
   list_inithead(&cache.free_bos);
   struct bo blocks[12] = {0};
   const size_t capacities[] = {64, 16, 4, 32, 8, 8, 64, 1, 128, 32, 12, 8};
   for (size_t i = 0; i < 12; i++) {
      blocks[i].size = capacities[i];
      insert_idle(&cache, &blocks[i]);
      sorted_and_idle(&cache);
   }
   struct bo *chosen = take_best_fit(&cache, 9);
   assert(chosen && chosen->size == 12 && chosen->active);
   sorted_and_idle(&cache);
   struct bo *maximum = evict_max(&cache);
   assert(maximum && maximum->size == 128 && maximum != chosen);
   chosen->active = false;
   insert_idle(&cache, chosen);
   sorted_and_idle(&cache);
   size_t budget = 64, total = 0, previous = SIZE_MAX;
   list_for_each_entry(struct bo, bo, &cache.free_bos, node)
      total += bo->size;
   while (total > budget) {
      struct bo *victim = evict_max(&cache);
      assert(victim && victim->size <= previous);
      total -= victim->size;
      previous = victim->size;
   }
   assert(total <= budget);
   sorted_and_idle(&cache);
   assert(!take_best_fit(&cache, 100000));
   sorted_and_idle(&cache);
   puts("UMA F3 idle sorted BO cache tests passed");
   return 0;
}
