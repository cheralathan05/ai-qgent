import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";

export const Route = createFileRoute("/verify-device")({
  head: () => ({ meta: [{ title: "Verify Device — APA-OS" }] }),
  component: VerifyDeviceRedirect,
});

function VerifyDeviceRedirect() {
  const navigate = useNavigate();
  useEffect(() => {
    navigate({ to: "/pair-device", replace: true });
  }, [navigate]);
  return null;
}
