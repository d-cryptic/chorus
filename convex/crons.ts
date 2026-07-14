import { cronJobs } from "convex/server";
import { internal } from "./_generated/api";

const crons = cronJobs();
// Times in UTC. 08:00 IST = 02:30 UTC.
crons.daily("daily enrich-rank cycle", { hourUTC: 2, minuteUTC: 30 }, internal.actions.runDailyCycle, {});
crons.daily("outcome tracking", { hourUTC: 4, minuteUTC: 0 }, internal.actions.measureOutcomes, {});
crons.weekly("rank-tune", { dayOfWeek: "sunday", hourUTC: 3, minuteUTC: 0 }, internal.rankTune.run, {});
export default crons;
