import time
import json
import os

class ClockCache:
    def __init__(self, capacity, checkpoint_file, checkpoint_interval, ttl=None):
        self.capacity = capacity
        self.clock = [None] * capacity  # The circular list representing the clock
        self.usage_bits = [0] * capacity  # Usage bits for the clock
        self.pointer = 0  # The clock hand
        self.cache_map = {}  # Maps keys to indices in the clock
        self.checkpoint_file = checkpoint_file
        self.checkpoint_interval = checkpoint_interval
        self.ttl = ttl
        self.load_cache()

    def _find_spot(self):
        while True:
            if self.usage_bits[self.pointer] == 0:
                return self.pointer
            else:
                # Give a second chance and clear the bit
                self.usage_bits[self.pointer] = 0
                self.pointer = (self.pointer + 1) % self.capacity

    def get(self, key):
        print(f"Trying to get key '{key}' from cache")
        if key in self.cache_map:
            idx = self.cache_map[key]
            self.usage_bits[idx] = 1  # Mark as recently used
            print(f"Cache hit for key '{key}'")
            return self.clock[idx][1]
        else:
            print(f"Cache miss for key '{key}'")
        return None

    def put(self, key, value):
        print(f"Putting key '{key}' in cache")
        if key in self.cache_map:
            idx = self.cache_map[key]
            self.clock[idx] = (key, value)
            self.usage_bits[idx] = 1
        else:
            idx = self._find_spot()
            if self.clock[idx] is not None:
                del self.cache_map[self.clock[idx][0]]
            self.clock[idx] = (key, value)
            self.usage_bits[idx] = 1
            self.cache_map[key] = idx
            self.pointer = (self.pointer + 1) % self.capacity

    def load_cache(self):
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    loaded_data = json.load(f)
                    if isinstance(loaded_data, dict):
                        for key, value in loaded_data.items():
                            self.put(key, value)
                        print(f"Cache loaded successfully with {len(loaded_data)} items.")
                    else:
                        print("Cache file format is incorrect, expected a dictionary.")
                        open(self.checkpoint_file, 'w').close()  
            except json.JSONDecodeError:
                print("Failed to decode JSON data from the cache file. The file may be empty or corrupted.")
                open(self.checkpoint_file, 'w').close()

    def checkpoint(self):
        try:
            with open(self.checkpoint_file, 'w') as f:
                cache_data = {self.clock[i][0]: self.clock[i][1] for i in range(self.capacity) if self.clock[i] is not None}
                json.dump(cache_data, f)
                print(f"Cache checkpointed with {len(cache_data)} items.")
        except IOError as e:
            print(f"IO error when writing to cache file: {e}")

    def purge_stale_entries(self):
        if self.ttl:
            current_time = time.time()
            to_purge = [i for i, entry in enumerate(self.clock) if entry and current_time - entry[2] > self.ttl]
            for i in to_purge:
                print(f"Purging stale cache entry for key '{self.clock[i][0]}'")
                del self.cache_map[self.clock[i][0]]
                self.clock[i] = None
                self.usage_bits[i] = 0

    def start_periodic_checkpoint(self):
        while True:
            time.sleep(self.checkpoint_interval)
            self.checkpoint()
            self.purge_stale_entries()


