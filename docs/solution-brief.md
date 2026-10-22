# Solution brief: AI skills fit for a growing FDE team

**For:** the Forward Deployed Engineering lead at a company scaling its FDE team (a
fictional customer). **Status:** working prototype, ready for a pilot.

## The problem

You are hiring and onboarding Forward Deployed Engineers quickly. The role needs a
specific mix of AI skills: building on AI APIs, turning AI into customer value, voice and
audio AI, and careful, responsible use. Today:

- candidates and new hires can't easily see how their AI skills compare with what the
  role needs, or what to work on first;
- leads give that feedback one conversation at a time, and inconsistently;
- general "AI literacy" quizzes don't reflect this role's priorities.

## Proposed solution

A short, eight-question voice interview that shows each person how their AI skills map to the FDE
role, and gives them a short, specific development plan. It is a **self-development
tool**: the result is indicative and is never used to make hiring decisions.

What each person gets:
- a fit percentage and band for the FDE role (for example "78%, Good fit");
- where they already meet the role, and the gaps that matter most, in order;
- the evidence from their own answers behind each score;
- 3–5 recommendations, each with a first step they can take this week.

## How it works

1. **Interview.** Seven questions, one for each skill area, read aloud with ElevenLabs
   text-to-speech. People answer by voice (transcribed by ElevenLabs Scribe) or by
   typing; typing is always allowed. An eighth, follow-up question targets the area that
   matters most to the role where the answers were thinnest.
2. **Scoring.** An AI model scores each area from 1 (Unaware) to 5 (Leading) against a
   fixed rubric, quoting what the person actually said. A quote that isn't in their
   answers is removed.
3. **Role fit.** The fit is calculated by simple, fixed arithmetic, not by the AI. Each
   area has a target score and an importance weight; the fit is the weighted share of
   targets met. The same scores always give the same result, and anyone can check it.

**How the role profile is built.** The targets and weights come only from the published
FDE job spec, and the profile names that source. The spec stresses Python and API
integration and owning customer delivery end to end, so those two areas carry the most
weight. Voice and audio AI, prompting and checking AI output come next; responsible use
and breadth of tools carry the least. The profile is a short, readable file: your team
can review it, change it, or add a profile for another role without any new software.

**Why the fit is indicative, not a hiring decision.** It rests on a short, self-reported
interview: it measures what people say, not what they do, and an AI model makes the
scores. People who are less comfortable speaking may come across less well (which is why
typing is always available). Every report carries the line "Indicative, based on a short
self-reported interview. Not a hiring assessment."

**Choice of AI model.** One setting switches between a cloud model (Claude: most
accurate, a report in about 15 seconds, well under 1 cent per interview) and a local
model that keeps answers on the laptop (private, but slower and noticeably less
accurate on today's hardware).

## Rollout plan

| Phase | Who | Length | Goal |
|---|---|---|---|
| **Pilot** | 5–10 volunteers from the current FDE team, plus the lead | 2 weeks | Check that the scores and gaps feel right to people who know the role. Tune the role profile. |
| **Team** | All new FDE hires during onboarding, and the existing team | 1 quarter | Use the plan in 1:1s; re-take after 3 months to see progress. |
| **Organisation** | Other customer-facing roles, each with its own profile | Following quarter | Add profiles; agree data handling with security and HR. |

Candidates are offered it only after the pilot and team phases, as an optional
self-check, kept apart from any hiring decision.

## Success metrics

- **Trust:** at least 80% of pilot users say their gaps "feel accurate"; leads agree with
  the band for most of their team.
- **Usefulness:** at least 70% start one recommended first step within two weeks.
- **Progress:** the average fit rises on re-assessment after a quarter.
- **Quality:** the scoring keeps passing its test set of example personas (currently
  20 of 21 scores in range and 3 of 3 fit bands with the cloud model).
- **Cost and speed:** under 1 cent and under 30 seconds per report in cloud mode.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| The fit % is read as a hiring verdict | Fixed disclaimer on every report; framed as self-development; not used in hiring; weights shown and explained. |
| The AI invents evidence or scores unfairly | Scores must quote the person's own words, invented quotes are removed, and a test set checks scoring before each change. |
| Bias against less confident speakers | Typing always allowed; the rubric rewards substance, not polish; plain-spoken examples in the test set. |
| The role profile doesn't match the real job | Built only from the published job spec; reviewed and tuned by the team in the pilot. |
| Personal answers leak | Answers kept in memory only, nothing saved by default; local mode keeps answers on the device; API keys never reach the browser. |
| Local mode is too slow or inaccurate | Use cloud mode by default; run local mode on stronger hardware or a larger model if privacy requires it. |

## Next steps

1. Agree the pilot group and a 30-minute review of the role profile with the FDE lead.
2. Run the 2-week pilot and collect feedback on accuracy and usefulness.
3. Decide on cloud or local mode with your security team.
4. Then consider: a team view for leads, more role profiles, and a real-time
   conversational interview on the ElevenLabs Agents Platform.
