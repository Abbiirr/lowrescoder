// Design decision: tui-textarea NOT adopted (M1)
//
// tui-textarea ships default keybindings that collide with app-owned controls:
//   Ctrl+K → palette  |  Ctrl+C → cancel/steer  |  Ctrl+J → confirm
//   Ctrl+U → clear    |  Ctrl+R → history search
//
// The library's event pipeline does not provide the full interception needed
// for multi-level Ctrl+C steer semantics.
//
// DECISION: Hand-roll composer in M4 (~100 LOC Vec<char> buffer).
// This is a design decision record, not a spike experiment.

#[cfg(test)]
mod tests {
    /// Decision: tui-textarea not adopted. See module doc for rationale.
    #[test]
    fn decision_tui_textarea_not_adopted() {
        // No experiment — the crate was not added as dev-dep to avoid
        // pulling in its transitive deps. The decision rests on API
        // documentation review and keybinding conflict analysis.
        //
        // To revisit: add tui-textarea = "0.x" to [dev-dependencies],
        // write tests that attempt full keybinding suppression.
    }
}
