# Ex 13.2: quantization trade-offs: quality vs speed vs size

The syllabus exercise is "quantize a small model to Q4 and Q8 with llama.cpp, then chart quality vs
speed vs size". The quantizing is done for real by `examples/python/m13/llama_quant.py` (llama.cpp
b12428 since 17 Nov 2026, `stories15M.gguf`); run it yourself:

```bash
LLAMA_CPP_DIR=... LLAMA_MODEL=.../stories15M.gguf uv run --project ../../python python -m m13.llama_quant
```

This exercise is the *decision* half, tested against the table that script produced on the course
box on 14 Nov 2026 with b12359, the v1.0.0 build (x86 CPU, 4 threads;
`tests/box_llama_b12359.json`; kept as fixed input, and a re-run on b12428 gave the same quality
numbers within noise). Write:

1. `pareto(rows)`: the rows no other row beats on all three of size (smaller), quality (lower
   `mean_kld`) and speed (higher `tg_tps`), in input order.
2. `pick(rows, max_mb, max_kld)`: the fastest row (by `tg_tps`) within both limits, or `None`.
3. `kv_cache_mb(n_layer, n_ctx, n_head_kv, head_dim, bytes_per_elem)`: K and V for every layer and
   position, in MB (1e6 bytes). Note what does *not* appear: the weight quant type.

These are x86 numbers. **The A73 run is untested**; the device numbers will differ, and so may the
ranking (Q4_K_M was slower than Q4_0 here).
