// Ex 11.2: split one oversized PR into a stack of reviewable PRs.
export interface Unit { name: string; lines: number; dependsOn: string[] }

export function splitStack(units: Unit[], limit: number): string[][] {
  // TODO: dependency order, greedy packing under `limit`, cycle/unknown errors.
  void limit;
  return [units.map((u) => u.name)];
}
