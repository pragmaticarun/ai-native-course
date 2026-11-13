# Ex 11.2: split an oversized agent PR into stacked PRs (TypeScript)

An agent opened one 960-line PR. Your team's limit (M11's example policy) is 400 changed lines per PR. Write
`splitStack(units, limit)` in `stack.ts`: given the PR's logical units (a name, a line count and the units it
depends on), return a stack of PRs (each a list of unit names) such that:

1. Every unit appears exactly once.
2. A unit only depends on units in the same PR or an earlier one (each PR in the stack builds and tests on its own).
3. Units are taken in dependency order; when several are ready, the one listed first in the input goes first.
4. Fill PRs greedily: add the next unit to the current PR if the total stays at or under `limit`, else start a new
   PR. A unit bigger than `limit` gets a PR to itself.
5. Throw an `Error` whose message contains `cycle` if the dependencies can't be ordered, or `unknown` if a unit
   depends on a name that isn't in the list.

Run: `EXERCISE_VARIANT=starter pnpm vitest run exercises/m11/ex2/ts`.
