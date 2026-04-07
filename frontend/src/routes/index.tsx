import { createFileRoute } from "@tanstack/react-router";
import { FileUpload } from "../components/FileUpload";

export const Route = createFileRoute("/")({
  component: FileUpload,
});
