# Lookmhee Shared Voting Dashboard

A read-only public standings dashboard for the Viral Hits Awards category. Tracks all 12 nominees, with a Lookmhee spotlight and historical percentages. No voting automation, login credentials, or private vote data.

## Publish from GitHub (no server required)

1. Create a **public GitHub repository** (e.g. `lookmhee-voting-dashboard`). The dashboard and its published aggregate team data will be public.
2. Upload the contents of this folder to the repository, preserving `.github/workflows/update.yml`.
3. Open repository **Settings → Actions → General → Workflow permissions** and select **Read and write permissions**, then save. (Some organizations restrict this setting.)
4. Open **Settings → Pages**. Under **Build and deployment**, select **Deploy from a branch**, branch **main**, folder **/docs**, then Save.
5. Open **Actions → Refresh public voting standings → Run workflow**. Wait for the workflow to finish. The first successful run creates `docs/index.html`.
6. The public dashboard address will usually be `https://YOUR-USERNAME.github.io/YOUR-REPO/`. GitHub Pages may take a few minutes to publish the first version. Share that URL with the voting group.

## Updates

GitHub Actions requests a new public snapshot every five minutes. **Scheduled jobs may be delayed or skipped** by GitHub, and GitHub may disable schedules in inactive repositories. The page displays the last successful snapshot timestamp. Refresh the page to see the latest published version. A failed scrape retains the last successfully published snapshot.

## Team participation

The first run creates `docs/team_participation.csv` with a header. To add voluntary aggregate reports, edit that CSV in GitHub using these columns:

`date_thailand,active_voters,reported_free_votes,reported_special_points,notes`

Example row (illustrative only):

`2026-10-23,50,250,0,Example only`

Do not publish member names, account identifiers, passwords, individual donation amounts, or other private information. The dashboard refreshes aggregate team data on the next successful run. **Never add the example row as real data.**

## Historical data from your Mac

If you have `viral_hits_standings.csv` from the old tracker, upload it to `docs/viral_hits_standings.csv` **before the first run** to retain your history. The tracker reads the existing file and appends new snapshots. It can read both the original tracker CSV format and the newer Command Center CSV format, but the first new update uses the Command Center columns; if your original CSV uses different columns, see the migration note below.

### Migration note: original CSV format

The original tracker uses columns `timestamp_utc,rank,nominee,votes,percentage,source`, while this tracker writes `timestamp_utc,rank,nominee,percentage,change_pp,rank_change,gap_to_leader_pp`. To import the original file, run `python migrate_history.py PATH_TO_OLD_CSV` locally, then upload the generated `docs/viral_hits_standings.csv` to GitHub. If your existing CSV already has the new columns, you can upload it directly.

## Notes

- Rankings reflect rounded public percentages. Equal percentages may not reflect true underlying ranks.
- Only public percentages are visible; exact vote counts cannot be inferred.
- This tool does not cast votes or circumvent website limits.
- The website can change its HTML layout, requiring an extractor update.
- To stop scheduled updates, disable the workflow in GitHub Actions.
