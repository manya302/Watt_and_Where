import { useMemo, useState } from "react";

const ADMIN_USERNAME = "admin";
const ADMIN_PASSWORD = "wattadmin2026";

const initialAppliances = [
  { id: 1, name: "Ceiling fan", type: "Fan", watts: 75, quantity: 2, hours: 8 },
  { id: 2, name: "LED bulb", type: "Lighting", watts: 9, quantity: 4, hours: 6 },
];

export default function AdminPage() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [appliances, setAppliances] = useState(initialAppliances);
  const [notice, setNotice] = useState("");

  const [form, setForm] = useState({
    name: "",
    type: "Other",
    watts: "",
    quantity: "1",
    hours: "1",
  });

  const monthlyUnits = (appliance) =>
    (Number(appliance.watts) *
      Number(appliance.quantity) *
      Number(appliance.hours) *
      30) /
    1000;

  const totalUnits = useMemo(
    () => appliances.reduce((sum, item) => sum + monthlyUnits(item), 0),
    [appliances]
  );

  function handleLogin(event) {
    event.preventDefault();

    if (username === ADMIN_USERNAME && password === ADMIN_PASSWORD) {
      setLoggedIn(true);
      setLoginError("");
      return;
    }

    setLoginError("Incorrect username or password. Please try again.");
  }

  function handleAddAppliance(event) {
    event.preventDefault();

    const watts = Number(form.watts);
    const quantity = Number(form.quantity);
    const hours = Number(form.hours);

    if (
      !form.name.trim() ||
      !Number.isFinite(watts) ||
      watts <= 0 ||
      !Number.isInteger(quantity) ||
      quantity < 1 ||
      !Number.isFinite(hours) ||
      hours < 0 ||
      hours > 24
    ) {
      setNotice("Enter a name, positive wattage, valid quantity, and 0–24 hours.");
      return;
    }

    const appliance = {
      ...form,
      id: Date.now(),
      name: form.name.trim(),
      watts,
      quantity,
      hours,
    };

    setAppliances((current) => [...current, appliance]);
    setForm({
      name: "",
      type: "Other",
      watts: "",
      quantity: "1",
      hours: "1",
    });
    setNotice(`${appliance.name} added successfully.`);
  }

  function removeAppliance(id) {
    setAppliances((current) => current.filter((item) => item.id !== id));
    setNotice("Appliance removed.");
  }

  if (!loggedIn) {
    return (
      <main className="admin-page">
        <section className="admin-login-card">
          <div className="admin-icon" aria-hidden="true">⚡</div>
          <p className="eyebrow">WATT & WHERE</p>
          <h1>Admin login</h1>
          <p className="muted">
            Sign in to manage the appliance list for this demo.
          </p>

          <form onSubmit={handleLogin} className="admin-form">
            <label htmlFor="admin-username">Username</label>
            <input
              id="admin-username"
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />

            <label htmlFor="admin-password">Password</label>
            <input
              id="admin-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />

            {loginError && (
              <p className="admin-error" role="alert">{loginError}</p>
            )}

            <button className="primary-button" type="submit">
              Sign in
            </button>
          </form>

          <p className="admin-footnote">
            Demo only: this fixed password is visible in the frontend code and
            is not suitable for securing a real admin account.
          </p>
        </section>
      </main>
    );
  }

  return (
    <main className="admin-page">
      <div className="admin-heading">
        <div>
          <p className="eyebrow">ADMIN WORKSPACE</p>
          <h1>Appliance manager</h1>
          <p className="muted">
            Add appliances and estimate their monthly energy consumption.
          </p>
        </div>

        <button
          className="secondary-button"
          onClick={() => setLoggedIn(false)}
          type="button"
        >
          Log out
        </button>
      </div>

      <section className="admin-stat">
        <span>Estimated monthly consumption</span>
        <strong>{totalUnits.toFixed(1)} kWh</strong>
        <small>Based on 30 days of use</small>
      </section>

      <div className="admin-content-grid">
        <section className="admin-panel">
          <h2>Add an appliance</h2>
          <p className="muted">
            Enter the appliance's rated power and average daily usage.
          </p>

          <form className="admin-form" onSubmit={handleAddAppliance}>
            <label htmlFor="appliance-name">Appliance name</label>
            <input
              id="appliance-name"
              placeholder="e.g. Refrigerator"
              value={form.name}
              onChange={(event) =>
                setForm({ ...form, name: event.target.value })
              }
              required
            />

            <label htmlFor="appliance-type">Category</label>
            <select
              id="appliance-type"
              value={form.type}
              onChange={(event) =>
                setForm({ ...form, type: event.target.value })
              }
            >
              <option>Lighting</option>
              <option>Fan</option>
              <option>Cooling</option>
              <option>Kitchen</option>
              <option>Entertainment</option>
              <option>Computing</option>
              <option>Other</option>
            </select>

            <div className="admin-form-row">
              <div>
                <label htmlFor="appliance-watts">Power (watts)</label>
                <input
                  id="appliance-watts"
                  type="number"
                  min="1"
                  step="any"
                  placeholder="100"
                  value={form.watts}
                  onChange={(event) =>
                    setForm({ ...form, watts: event.target.value })
                  }
                  required
                />
              </div>

              <div>
                <label htmlFor="appliance-quantity">Quantity</label>
                <input
                  id="appliance-quantity"
                  type="number"
                  min="1"
                  step="1"
                  value={form.quantity}
                  onChange={(event) =>
                    setForm({ ...form, quantity: event.target.value })
                  }
                  required
                />
              </div>
            </div>

            <label htmlFor="appliance-hours">Hours used per day</label>
            <input
              id="appliance-hours"
              type="number"
              min="0"
              max="24"
              step="0.5"
              value={form.hours}
              onChange={(event) =>
                setForm({ ...form, hours: event.target.value })
              }
              required
            />

            {notice && <p className="admin-notice" role="status">{notice}</p>}

            <button className="primary-button" type="submit">
              + Add appliance
            </button>
          </form>
        </section>

        <section className="admin-panel">
          <div className="admin-list-heading">
            <div>
              <h2>Your appliances</h2>
              <p className="muted">{appliances.length} appliances</p>
            </div>
          </div>

          {appliances.length === 0 ? (
            <p className="muted">No appliances yet. Add one to get started.</p>
          ) : (
            <div className="appliance-list">
              {appliances.map((item) => (
                <article className="appliance-item" key={item.id}>
                  <div className="appliance-item-icon" aria-hidden="true">
                    ⚡
                  </div>

                  <div className="appliance-item-info">
                    <strong>{item.name}</strong>
                    <span>
                      {item.type} · {item.quantity} × {item.watts} W
                    </span>
                    <span>{item.hours} hours/day</span>
                  </div>

                  <div className="appliance-item-usage">
                    <strong>{monthlyUnits(item).toFixed(1)}</strong>
                    <span>kWh/month</span>
                    <button
                      type="button"
                      className="remove-button"
                      onClick={() => removeAppliance(item.id)}
                      aria-label={`Remove ${item.name}`}
                    >
                      Remove
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}