import { useMemo, useState } from "react";
import { STRINGS, formatUnits } from "../strings.js";
import {
  SAMPLE_EQUIPMENT,
  EQUIPMENT_TYPES,
  CONTROL_TYPES,
  EQUIPMENT_PRESETS,
  estimateMonthlyUnits,
} from "../data/sampleEquipment.js";

function newId() {
  return `equipment-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function copySampleList() {
  return SAMPLE_EQUIPMENT.map((item) => ({ ...item }));
}

function validateItem(item) {
  const errors = {};

  if (!item.name.trim()) {
    errors.name = STRINGS.committee.invalidName;
  }

  if (
    !Number.isInteger(Number(item.quantity)) ||
    Number(item.quantity) < 1
  ) {
    errors.quantity = STRINGS.committee.invalidQuantity;
  }

  if (
    item.powerKw === "" ||
    !Number.isFinite(Number(item.powerKw)) ||
    Number(item.powerKw) <= 0
  ) {
    errors.powerKw = STRINGS.committee.invalidPower;
  }

  if (
    item.hoursPerDay === "" ||
    !Number.isFinite(Number(item.hoursPerDay)) ||
    Number(item.hoursPerDay) < 0 ||
    Number(item.hoursPerDay) > 24
  ) {
    errors.hoursPerDay = STRINGS.committee.invalidHours;
  }

  if (!EQUIPMENT_TYPES.some((type) => type.value === item.type)) {
    errors.type = STRINGS.committee.invalidType;
  }

  if (!CONTROL_TYPES.some((control) => control.value === item.control)) {
    errors.control = STRINGS.committee.invalidControl;
  }

  return errors;
}

function updateField(item, field, value) {
  return { ...item, [field]: value };
}

function ItemField({
  id,
  label,
  value,
  error,
  onChange,
  type = "text",
  min,
  max,
  step,
}) {
  const errorId = error ? `${id}-error` : undefined;

  return (
    <div className="equipment-field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type={type}
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={Boolean(error)}
        aria-describedby={errorId}
      />
      {error && (
        <p className="field-error" id={errorId}>
          {error}
        </p>
      )}
    </div>
  );
}

function ItemSelect({
  id,
  label,
  value,
  options,
  error,
  onChange,
}) {
  const errorId = error ? `${id}-error` : undefined;

  return (
    <div className="equipment-field">
      <label htmlFor={id}>{label}</label>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={Boolean(error)}
        aria-describedby={errorId}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error && (
        <p className="field-error" id={errorId}>
          {error}
        </p>
      )}
    </div>
  );
}

function EquipmentCard({
  item,
  onChange,
  onRemove,
  index,
}) {
  const errors = validateItem(item);
  const isLight = item.type === "lighting";
  const monthlyUnits = estimateMonthlyUnits({
    ...item,
    quantity: Number(item.quantity) || 0,
    powerKw: Number(item.powerKw) || 0,
    hoursPerDay: Number(item.hoursPerDay) || 0,
  });

  function change(field, value) {
    onChange(item.id, field, value);
  }

  const powerValue = isLight
    ? (Number(item.powerKw) || 0) * 1000
    : item.powerKw;

  return (
    <article className="equipment-card">
      <div className="equipment-card-heading">
        <div>
          <p className="eyebrow">Equipment {index + 1}</p>
          <h3>{item.name.trim() || "New equipment"}</h3>
        </div>

        <button
          type="button"
          className="secondary-button remove-button"
          onClick={() => onRemove(item.id)}
          aria-label={`${STRINGS.committee.remove}: ${item.name || "new equipment"}`}
        >
          {STRINGS.committee.remove}
        </button>
      </div>

      <div className="equipment-fields">
        <ItemField
          id={`${item.id}-name`}
          label={STRINGS.committee.name}
          value={item.name}
          error={errors.name}
          onChange={(value) => change("name", value)}
        />

        <ItemSelect
          id={`${item.id}-type`}
          label={STRINGS.committee.type}
          value={item.type}
          options={EQUIPMENT_TYPES}
          error={errors.type}
          onChange={(value) => change("type", value)}
        />

        <ItemField
          id={`${item.id}-quantity`}
          label={STRINGS.committee.quantity}
          value={item.quantity}
          error={errors.quantity}
          type="number"
          min="1"
          step="1"
          onChange={(value) => change("quantity", value)}
        />

        <ItemField
          id={`${item.id}-power`}
          label={`${STRINGS.committee.power} (${isLight ? "W" : "kW"})`}
          value={powerValue}
          error={errors.powerKw}
          type="number"
          min="0.001"
          step={isLight ? "1" : "0.1"}
          onChange={(value) =>
            change("powerKw", value === "" ? "" : Number(value) / (isLight ? 1000 : 1))
          }
        />

        <ItemField
          id={`${item.id}-hours`}
          label={STRINGS.committee.hours}
          value={item.hoursPerDay}
          error={errors.hoursPerDay}
          type="number"
          min="0"
          max="24"
          step="0.25"
          onChange={(value) =>
            change("hoursPerDay", value === "" ? "" : Number(value))
          }
        />

        <ItemSelect
          id={`${item.id}-control`}
          label={STRINGS.committee.control}
          value={item.control}
          options={CONTROL_TYPES}
          error={errors.control}
          onChange={(value) => change("control", value)}
        />
      </div>

      <p className="estimate-line">
        <strong>{STRINGS.committee.estimate}:</strong>{" "}
        about {formatUnits(monthlyUnits)} units per month
      </p>
    </article>
  );
}

export default function CommitteePreview() {
  const [items, setItems] = useState(copySampleList);
  const [preset, setPreset] = useState("borewell");
  const [notice, setNotice] = useState("");
  const [hasEdited, setHasEdited] = useState(false);
  const [pendingRemoval, setPendingRemoval] = useState(null);

  const totalUnits = useMemo(
    () => items.reduce((total, item) => total + estimateMonthlyUnits({
      ...item,
      quantity: Number(item.quantity) || 0,
      powerKw: Number(item.powerKw) || 0,
      hoursPerDay: Number(item.hoursPerDay) || 0,
    }), 0),
    [items]
  );

  const allValid = items.every(
    (item) => Object.keys(validateItem(item)).length === 0
  );

  const groupedItems = EQUIPMENT_TYPES.map((type) => ({
    ...type,
    items: items.filter((item) => item.type === type.value),
  })).filter((group) => group.items.length > 0);

  function editItem(id, field, value) {
    setItems((current) =>
      current.map((item) =>
        item.id === id ? updateField(item, field, value) : item
      )
    );
    setHasEdited(true);
    setNotice("");
  }

  function addItem() {
    const selected = EQUIPMENT_PRESETS.find(
      (item) => item.value === preset
    );

    if (!selected) return;

    setItems((current) => [
      ...current,
      { ...selected.item, id: newId() },
    ]);
    setHasEdited(true);
    setNotice("");
  }

  function requestRemove(id) {
    setPendingRemoval(id);
  }

  function confirmRemove() {
    setItems((current) =>
      current.filter((item) => item.id !== pendingRemoval)
    );
    setPendingRemoval(null);
    setHasEdited(true);
    setNotice("");
  }

  function resetItems() {
    const confirmed = window.confirm(STRINGS.committee.confirmReset);
    if (!confirmed) return;

    setItems(copySampleList());
    setHasEdited(false);
    setNotice("");
    setPendingRemoval(null);
  }

  function savePreview() {
    if (!allValid) return;

    setNotice(STRINGS.committee.saveMessage);
  }

  return (
    <main id="main-content" className="page-content committee-page">
      <div className="preview-banner" role="status">
        <strong>{STRINGS.committee.previewBanner}</strong>
      </div>

      <div className="page-heading">
        <div>
          <p className="eyebrow">Committee tools</p>
          <h1>{STRINGS.committee.title}</h1>
          <p>{STRINGS.committee.helper}</p>
        </div>
        <a className="text-link" href="#/">
          {STRINGS.app.dashboardLink}
        </a>
      </div>

      {hasEdited && (
        <p className="unsaved-message" role="status">
          {STRINGS.committee.unsaved}. {STRINGS.committee.savedLocallyNote}
        </p>
      )}

      <section className="card equipment-summary" aria-live="polite">
        <div>
          <p className="eyebrow">{STRINGS.committee.totalEstimate}</p>
          <p className="total-estimate">
            About {formatUnits(totalUnits)} units per month
          </p>
          <p className="muted-copy">{STRINGS.committee.roughEstimate}</p>
        </div>
        <span className="estimate-symbol" aria-hidden="true">
          kWh
        </span>
      </section>

      <section className="equipment-toolbar" aria-label="Equipment actions">
        <div className="preset-picker">
          <label htmlFor="equipment-preset">Choose equipment to add</label>
          <select
            id="equipment-preset"
            value={preset}
            onChange={(event) => setPreset(event.target.value)}
          >
            {EQUIPMENT_PRESETS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>

          <button
            type="button"
            className="primary-button"
            onClick={addItem}
          >
            {STRINGS.committee.addEquipment}
          </button>
        </div>

        <button
          type="button"
          className="secondary-button"
          onClick={resetItems}
        >
          {STRINGS.committee.reset}
        </button>
      </section>

      {pendingRemoval && (
        <section className="card confirm-card" role="alertdialog" aria-labelledby="remove-title">
          <h2 id="remove-title">{STRINGS.committee.removePrompt}</h2>
          <p>
            {items.find((item) => item.id === pendingRemoval)?.name}
          </p>
          <div className="button-row">
            <button
              type="button"
              className="primary-button"
              onClick={confirmRemove}
            >
              {STRINGS.committee.yes}
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={() => setPendingRemoval(null)}
            >
              {STRINGS.committee.no}
            </button>
          </div>
        </section>
      )}

      <div className="equipment-groups">
        {groupedItems.map((group) => (
          <section
            className="equipment-group"
            key={group.value}
            aria-labelledby={`group-${group.value}`}
          >
            <h2 id={`group-${group.value}`}>{group.label}</h2>

            <div className="equipment-list">
              {group.items.map((item) => (
                <EquipmentCard
                  key={item.id}
                  item={item}
                  index={items.findIndex((entry) => entry.id === item.id)}
                  onChange={editItem}
                  onRemove={requestRemove}
                />
              ))}
            </div>
          </section>
        ))}
      </div>

      <section className="save-area">
        <p className="muted-copy">
          {STRINGS.committee.fullVersionNote}
        </p>

        <button
          type="button"
          className="primary-button save-button"
          onClick={savePreview}
          disabled={!allValid}
        >
          {STRINGS.committee.save}
        </button>

        {!allValid && (
          <p className="field-error" role="status">
            Fix the highlighted fields before continuing.
          </p>
        )}

        {notice && (
          <p className="success-message" role="status">
            {notice}
          </p>
        )}
      </section>
    </main>
  );
}