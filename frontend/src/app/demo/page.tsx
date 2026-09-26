import type { Metadata } from "next";
import { DemoWorkspace } from "@/components/DemoWorkspace";

export const metadata: Metadata = {
  title: "Interactive Demo",
  description:
    "Trải nghiệm RAGTutor với dữ liệu mẫu, không cần tài khoản và không gửi dữ liệu lên máy chủ.",
};

export default function DemoPage() {
  return <DemoWorkspace />;
}
