import { useEffect, useState } from "react";
import { createItem, deleteItem, fetchItems, type Item } from "../api";

export default function ItemsPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchItems()
      .then(setItems)
      .catch(() => setError("Could not load items."))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      const item = await createItem(name.trim(), description.trim());
      setItems((prev) => [...prev, item]);
      setName("");
      setDescription("");
    } catch {
      setError("Failed to create item.");
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteItem(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
    } catch {
      setError("Failed to delete item.");
    }
  }

  return (
    <div className="page">
      <h2>Items</h2>
      <p className="muted">Original demo resource (kept for reference).</p>

      <form onSubmit={handleCreate} className="form">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" required />
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Description (optional)"
        />
        <button type="submit">Add</button>
      </form>

      {error && <p className="error">{error}</p>}

      {loading ? (
        <p>Loading…</p>
      ) : items.length === 0 ? (
        <p className="empty">No items yet. Add one above.</p>
      ) : (
        <ul className="list">
          {items.map((item) => (
            <li key={item.id} className="list-item">
              <div>
                <strong>{item.name}</strong>
                {item.description && <p>{item.description}</p>}
              </div>
              <button
                onClick={() => handleDelete(item.id)}
                className="delete"
                aria-label={`Delete ${item.name}`}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
