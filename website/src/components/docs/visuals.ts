// Which docs pages open with a visual header, keyed by Starlight's route id (the page slug, as
// docs/publish.json sets it). PageTitle.astro renders the matching component under the page title;
// a page that is not listed keeps the plain title.
import BatteryVisual from './BatteryVisual.astro';
import DeterminismTiers from './DeterminismTiers.astro';
import EvaluationPipeline from './EvaluationPipeline.astro';
import GatesVisual from './GatesVisual.astro';
import LayerStack from './LayerStack.astro';
import ReleaseFlow from './ReleaseFlow.astro';
import RoadmapVisual from './RoadmapVisual.astro';
import RoleLanes from './RoleLanes.astro';
import StageArc from './StageArc.astro';
import SubstrateOverview from './SubstrateOverview.astro';

type Visual = typeof EvaluationPipeline;

export const visuals: Readonly<Record<string, Visual>> = {
  research: EvaluationPipeline,
  'research/origins': StageArc,
  'research/roadmap': RoadmapVisual,
  'research/gates': GatesVisual,
  'research/test-battery': BatteryVisual,
  'research/engineering': DeterminismTiers,
  'research/disclosure-policy': ReleaseFlow,
  'substrate/overview': SubstrateOverview,
  'substrate/architecture': LayerStack,
  'substrate/methodology': RoleLanes,
};

/** The visual header for a route id, if the page has one. */
export function visualFor(id: string): Visual | undefined {
  return Object.hasOwn(visuals, id) ? visuals[id] : undefined;
}
