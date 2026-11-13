# Ex 14.2: an ffmpeg argument allowlist (TypeScript)

An agent proposes ffmpeg arguments as a list. Write `checkArgs(args, root)` returning a list of
problems (empty = allowed):

- only these options: `-i`, `-ss`, `-t`, `-to`, `-vf`, `-af`, `-c:v`, `-c:a`, `-b:a`, `-ar`, `-ac`,
  `-frames:v`, `-an`, `-vn`, `-y`; anything else is `"option not allowed: <opt>"` (that includes
  `-f`, which can select the `concat` demuxer or a network muxer, and `-filter_complex` / `-lavfi`)
- every input (`-i`) and the output (last argument) must be a plain relative path inside `root`:
  no `proto:` prefix (`concat:`, `http:`, `file:`, `pipe:`, `tcp:`...), no absolute path, no `..`
  escape; report `"protocol not allowed: <value>"` or `"path escapes root: <value>"`
- filter strings (`-vf`, `-af`) must not use `movie=`/`amovie=` sources (they open files) or
  `sendcmd`/`zmq`; report `"filter not allowed: <name>"`

The Python media tools (`examples/python/m14/media_tools.py`) never let the model write flags at all;
this is the next-best design when you must accept arguments.
