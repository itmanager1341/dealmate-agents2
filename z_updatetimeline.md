| Day       | Deliverable                                                                                     | AI speed-up tip                                            |
| --------- | ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| **0-2**   | Refactor helpers into `Tool` subclasses (`pdf_to_text`, `whisper_transcribe`, `excel_to_json`). | Use GPT-4 to auto-generate docstrings & unit tests.        |
| **3-5**   | Implement `Agent` base + move existing `financial_agent` & friends to toolbox pattern.          | Let GPT-4 convert old agent code → new interface.          |
| **6-8**   | Add `PlanningAgent` + simple reflector critic loop.                                             | Prompt GPT-4 to draft reflection prompts.                  |
| **9-11**  | Add `agent_runs`, `agent_plans` tables, logging decorator.                                      | Copilot for migrations.                                    |
| **12-14** | Implement `scheduled_runs` + pg\_cron worker Edge Function.                                     | GPT-4 to write SQL & TypeScript.                           |
| **15-17** | Observability dashboard (Lovable) reading `agent_runs`.                                         | GPT-4 generate shadcn/ui table & chart components.         |
| **18-20** | Cost-control middleware (token trimming, caching sketch).                                       | Use GPT-4 to simulate token counts & find trim heuristics. |
