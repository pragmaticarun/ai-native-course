// Ex 11.2: split one oversized PR into a stack of reviewable PRs.
export interface Unit { name: string; lines: number; dependsOn: string[] }

function order(units: Unit[]): Unit[] {
  const names = new Set(units.map((u) => u.name));
  for (const u of units) {
    for (const d of u.dependsOn) if (!names.has(d)) throw new Error(`unknown dependency ${d} of ${u.name}`);
  }
  const done = new Set<string>();
  const out: Unit[] = [];
  while (out.length < units.length) {
    const next = units.find((u) => !done.has(u.name) && u.dependsOn.every((d) => done.has(d)));
    if (!next) throw new Error(`dependency cycle among ${units.filter((u) => !done.has(u.name)).map((u) => u.name).join(", ")}`);
    done.add(next.name);
    out.push(next);
  }
  return out;
}

export function splitStack(units: Unit[], limit: number): string[][] {
  const stack: string[][] = [];
  let current: string[] = [];
  let size = 0;
  for (const u of order(units)) {
    if (current.length > 0 && size + u.lines > limit) {
      stack.push(current);
      current = [];
      size = 0;
    }
    current.push(u.name);
    size += u.lines;
  }
  if (current.length > 0) stack.push(current);
  return stack;
}
