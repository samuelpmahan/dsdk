# The risk frontier: how much death buys how much gold
kind: instrument
idea: Give the probabilistic agent a risk limit (never step on a square whose chance of death is above L) and sweep L from 0 to 1 over seeds 1 to 300. Plot gold found against deaths, with an exact 95% interval on each rate, so the Lab shows the whole trade-off curve instead of two endpoints.
why it's interesting: The Lab now shows only "never gamble" (0 deaths, 71 gold) and "always gamble" (146 deaths, 133 gold). The curve should have a knee: a limit where most of the extra gold arrives at a small cost in lives. It is also the first place the exact intervals from dsdk.prob matter visibly, because the low-death end rests on very few events.
smallest experiment: A new function in dsdk.worlds.wumpus, run_agent with a max_risk argument, and sweep_rates over six limits; render a small table first, then a scatter. The page reruns the same sweep with its own agent and shows agree or disagree per limit.
reuses: dsdk.worlds.wumpus.stuck_risk, provably_safe, run_agent, sweep_rates; dsdk.prob.exact_interval; the Lab's rate table and its page-side agent
probe: With a limit of 0, 1/10, 1/5, 1/3, 1/2 and 1 the agent died in 0, 0, 3, 21, 32 and 146 of 300 caves and found gold in 79, 79, 86, 102, 109 and 133. A limit of 1/5 buys 7 more golds than 0 for 3 deaths (3 deaths, interval 0.2% to 2.9%); 1/2 buys 30 more for 32 deaths. Computed read-only with the repo's wumpus functions and a probe loop; the command is in the report of this turn's probe, not in the repo.
score: surprise=4 cost=2 reuse=5
