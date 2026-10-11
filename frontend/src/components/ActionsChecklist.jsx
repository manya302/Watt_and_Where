import { useState } from "react";
import { STRINGS } from "../strings.js";

function getActionText(action) {
  if (typeof action === "string") return action;

  return (
    action?.description ||
    action?.action ||
    action?.title ||
    ""
  );
}

export default function ActionsChecklist({
  actions = [],
}) {
  const [completed, setCompleted] = useState({});

  const validActions = Array.isArray(actions)
    ? actions.filter((action) => getActionText(action))
    : [];

  function toggleAction(index) {
    setCompleted((current) => ({
      ...current,
      [index]: !current[index],
    }));
  }

  return (
    <section className="panel actions-panel" aria-labelledby="actions-title">
      <p className="eyebrow">
        {STRINGS.dashboard?.actionsEyebrow || "What you can do"}
      </p>

      <h2 id="actions-title">
        {STRINGS.dashboard?.actionsTitle || "Recommended next steps"}
      </h2>

      {validActions.length === 0 ? (
        <p>
          {STRINGS.dashboard?.noActions ||
            "There are no specific actions to show for this month."}
        </p>
      ) : (
        <>
          <p className="muted-note">
            {STRINGS.dashboard?.checklistNote ||
              "Tick an item when your apartment team has reviewed it."}
          </p>

          <ul className="actions-checklist">
            {validActions.map((action, index) => (
              <li key={`${getActionText(action)}-${index}`}>
                <label className="checklist-item">
                  <input
                    type="checkbox"
                    checked={Boolean(completed[index])}
                    onChange={() => toggleAction(index)}
                  />
                  <span
                    className={
                      completed[index] ? "checklist-item__done" : ""
                    }
                  >
                    {getActionText(action)}
                  </span>
                </label>
              </li>
            ))}
          </ul>

          <p className="muted-note">
            {Object.values(completed).filter(Boolean).length} of{" "}
            {validActions.length}{" "}
            {STRINGS.dashboard?.actionsReviewed || "reviewed"}
          </p>
        </>
      )}
    </section>
  );
}