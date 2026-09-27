import { ProjectRoadmap } from "@/components/ProjectRoadmap";

export default async function ProjectRoadmapPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return <ProjectRoadmap projectId={projectId} />;
}
