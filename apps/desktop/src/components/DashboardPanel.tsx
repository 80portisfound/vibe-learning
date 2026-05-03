import { Activity, BookOpen, Bug, CheckCircle2, GitBranch, Target } from 'lucide-react';
import type { DashboardProjection } from '../api';

export function DashboardPanel({ dashboard }: { dashboard: DashboardProjection | null }) {
  const overview = dashboard?.overview;
  return (
    <aside className="dashboard">
      <section className="panel dashboard-overview">
        <div className="panel-title"><Target size={16} /> Overview</div>
        <div className={`status-banner ${overview?.status ?? 'idle'}`}>
          <span>{overview?.status ?? 'idle'}</span>
          <strong>{overview?.progress_percent ?? 0}%</strong>
        </div>
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${overview?.progress_percent ?? 0}%` }} />
        </div>
        <div className="summary-grid">
          <SummaryMetric label="Done" value={overview?.completed_count ?? 0} />
          <SummaryMetric label="Active" value={overview?.in_progress_count ?? 0} />
          <SummaryMetric label="Files" value={overview?.touched_file_count ?? 0} />
          <SummaryMetric label="Blocks" value={overview?.blocker_count ?? 0} />
        </div>
        {overview?.next_action && (
          <div className="dashboard-field">
            <span>Next action</span>
            <p>{overview.next_action}</p>
          </div>
        )}
        {overview?.last_activity && (
          <div className="dashboard-field">
            <span>Last activity</span>
            <p>{overview.last_activity}</p>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-title"><CheckCircle2 size={16} /> Implementation</div>
        {dashboard?.implementation.current_goal && (
          <div className="dashboard-field">
            <span>Goal</span>
            <p>{dashboard.implementation.current_goal}</p>
          </div>
        )}
        <div className="muted">Test status: {dashboard?.implementation.test_status ?? 'unknown'}</div>
        {(dashboard?.implementation.in_progress_changes?.length ?? 0) > 0 && (
          <>
            <div className="dashboard-label">In progress</div>
            <ul>
              {dashboard?.implementation.in_progress_changes.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </>
        )}
        {(dashboard?.implementation.completed_changes?.length ?? 0) > 0 && <div className="dashboard-label">Completed</div>}
        <ul>
          {(dashboard?.implementation.completed_changes ?? []).map((item) => <li key={item}>{item}</li>)}
        </ul>
        {(dashboard?.implementation.blockers?.length ?? 0) > 0 && <div className="dashboard-label">Blockers</div>}
        <ul>
          {(dashboard?.implementation.blockers ?? []).map((item) => <li key={item}>{item}</li>)}
        </ul>
        {(dashboard?.implementation.next_steps?.length ?? 0) > 0 && <div className="dashboard-label">Next</div>}
        <ul>
          {(dashboard?.implementation.next_steps ?? []).map((item) => <li key={item}>{item}</li>)}
        </ul>
      </section>

      <section className="panel">
        <div className="panel-title"><Activity size={16} /> Activity</div>
        <ul className="activity-list">
          {(dashboard?.activity ?? []).slice(-8).map((item, index) => (
            <li key={`${item.kind}:${item.summary}:${index}`} className={`activity-item ${item.stream || 'tool'}`}>
              <span>{item.kind}</span>
              {item.summary}
            </li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <div className="panel-title"><BookOpen size={16} /> Concepts</div>
        <div className="muted">{overview?.concept_count ?? 0} concepts captured</div>
        <ul>
          {(dashboard?.concepts ?? []).map((item) => <li key={item.concept}>{item.concept}: {item.short_summary}</li>)}
        </ul>
      </section>

      <section className="panel">
        <div className="panel-title"><GitBranch size={16} /> Decisions & Changes</div>
        <div className="muted">{overview?.decision_count ?? 0} decisions tracked</div>
        {(dashboard?.decisions?.length ?? 0) > 0 && <div className="dashboard-label">Decisions</div>}
        <ul>
          {(dashboard?.decisions ?? []).map((item) => (
            <li key={`${item.user_request}:${item.outcome}`}>{item.user_request}: {item.outcome}</li>
          ))}
        </ul>
        {(dashboard?.before_after?.length ?? 0) > 0 && <div className="dashboard-label">Changes</div>}
        <ul>
          {(dashboard?.before_after ?? []).map((item) => <li key={item.file_path}>{item.file_path}: {item.after_summary}</li>)}
        </ul>
      </section>

      <section className="panel">
        <div className="panel-title"><Bug size={16} /> Error Learning</div>
        <ul>
          {(dashboard?.errors ?? []).map((item) => <li key={item.error_message}>{item.error_message}: {item.root_cause_summary}</li>)}
        </ul>
      </section>
    </aside>
  );
}

function SummaryMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="summary-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
