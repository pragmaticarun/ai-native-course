# Ex 14.2: an ffmpeg argument allowlist (TypeScript)

An agent proposes ffmpeg arguments as a list. Write `checkArgs(args, root)` returning a list of
problems (empty = allowed):

- only these options: `-i`, `-ss`, `-t`, `-to`, `-vf`, `-af`, `-c:v`, `-c:a`, `-b:a`, `-ar`, `-ac`,
  `-frames:v`, `-an`, `-vn`, `-y`; anything else is `"option not allowed: <opt>"` (that includes
  `-f`, which can select the `concat` demuxer or a network muxer, and `-filter_complex` / `-lavfi`)
- every input (`-i`) and the output (last argument) must be a plain relative path inside `root`:
  no `proto:` prefix (`concat:`, `http:`, `file:`, `pipe:`, `tcp:`, and FFmpeg 9.1's `libcurl:`...), no absolute path, no `..`
  escape; report `"protocol not allowed: <value>"` or `"path escapes root: <value>"`
- filter strings (`-vf`, `-af`) must not use `movie=`/`amovie=` sources (they open files) or
  `sendcmd`/`zmq`; report `"filter not allowed: <name>"`

FFmpeg 9.1 "Gauss" (20 Nov 2026) added a `libcurl` protocol: `libcurl:https://...` forces it, and
the generic `-prefer_libcurl 1` option sends every `http(s)` URL through it. A check that names the
protocols it blocks would have missed the new one. Rejecting any `scheme:` prefix and allowing only
listed options covers both cases, and the tests check that.

The Python media tools (`examples/python/m14/media_tools.py`) never let the model write flags at all;
this is the next-best design when you must accept arguments.
