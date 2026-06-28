import { QueryClient } from "@tanstack/react-query";
import { createRouter, redirect } from "@tanstack/react-router";
import { routeTree } from "./routeTree.gen";
import { entStore, hasTokens } from "./lib/apa/enterprise";

const PUBLIC_ROUTES = ["/login", "/register", "/forgot-password", "/reset-password", "/verify-email"];

// Routes that require device pairing
const DEVICE_REQUIRED_ROUTES = [
  "/dashboard", "/console", "/settings", "/screen", "/screen-analysis",
  "/screen-intelligence", "/screen-memory", "/world", "/workspaces",
  "/twin", "/timeline", "/memory", "/brain", "/life", "/goals", "/career",
  "/employee", "/future-self", "/learning", "/research", "/predictions",
  "/reality", "/notifications", "/approvals", "/audit", "/errors", "/events",
  "/automations", "/mobile-agent", "/phone-intelligence", "/navigation",
  "/observatory", "/onboarding", "/organization", "/profile", "/projects",
  "/ready", "/replay", "/setup-check", "/system", "/verification",
  "/app-knowledge", "/assistant", "/elements", "/emergency",
  "/knowledge-connect", "/workflows", "/agents", "/agents/monitor",
  "/knowledge", "/knowledge/chat", "/knowledge/graph", "/knowledge/search",
  "/knowledge/sources", "/documents",
];

export const getRouter = () => {
  const queryClient = new QueryClient();

  const router = createRouter({
    routeTree,
    context: { queryClient },
    scrollRestoration: true,
    defaultPreloadStaleTime: 0,
    defaultPreload: "intent",
    beforeLoad: async ({ location }) => {
      const { authenticated } = entStore.get();
      const isPublic = PUBLIC_ROUTES.includes(location.pathname);
      const tokensExist = hasTokens();

      if (!authenticated && !isPublic) {
        if (tokensExist) {
          // Tokens exist but store not hydrated - allow through, app will check
          return;
        }
        throw redirect({ to: "/login" });
      }

      if (authenticated && isPublic && location.pathname !== "/reset-password" && location.pathname !== "/verify-email") {
        // After login, check if user has a device connected before redirecting
        // The login page will handle device check and redirect accordingly
        throw redirect({ to: "/pair-device" });
      }
    },
  });

  return router;
};
