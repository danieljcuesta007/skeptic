# Claude Code adapter

Session IDs and hook events are host-reported observations. SessionStart supplies session/project hints; Stop indicates an agent response boundary, not process quiescence. SessionEnd does not prove all external tools stopped. No automatic provider launch, instruction injection or write is permitted from an event.

Existing consent-gated Claude transcript recovery remains the supported historical adapter. A Terminal tab/native PID record is an uncertain hint until independently confirmed. Returning context requires reconciliation; `fg` alone is insufficient.

Development hook adapter accepts bounded JSON on stdin and emits one structured local event. Configure only disposable settings for testing. Live hook activation remains separately gated.
