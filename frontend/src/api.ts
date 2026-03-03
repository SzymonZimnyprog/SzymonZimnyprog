const BASE = "/api";

export interface Item {
  id: number;
  name: string;
  description: string;
}

export async function fetchItems(): Promise<Item[]> {
  const res = await fetch(`${BASE}/items/`);
  if (!res.ok) throw new Error("Failed to fetch items");
  return res.json();
}

export async function createItem(
  name: string,
  description: string
): Promise<Item> {
  const res = await fetch(`${BASE}/items/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description }),
  });
  if (!res.ok) throw new Error("Failed to create item");
  return res.json();
}

export async function deleteItem(id: number): Promise<void> {
  const res = await fetch(`${BASE}/items/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete item");
}
