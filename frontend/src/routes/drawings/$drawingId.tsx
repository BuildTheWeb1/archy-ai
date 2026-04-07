import { createFileRoute } from "@tanstack/react-router";
import { DrawingDetail } from "../../components/DrawingDetail";

export const Route = createFileRoute("/drawings/$drawingId")({
  component: DrawingDetailPage,
});

function DrawingDetailPage() {
  const { drawingId } = Route.useParams();
  return <DrawingDetail drawingId={drawingId} />;
}
