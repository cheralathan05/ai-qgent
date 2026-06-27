import { QueryClient } from "@tanstack/react-query";
import { createRouter, redirect } from "@tanstack/react-router";
import { routeTree } from "./routeTree.gen";
import { entStore, hasTokens } from "./lib/apa/enterprise";

const PUBLIC_ROUTES = ["/login", "/register", "/forgot-password", "/reset-password", "/verify-email"];

export const getRouter = () => {
  const queryClient = new QueryClient();

  const router = createRouter({
    routeTree,
    context: { queryClient },
    scrollRestoration: true,
    defaultPreloadStaleTime: 0,
    defaultPreload: "intent",
    beforeLoad: ({ location }) => {
      const { authenticated } = entStore.get();
      const isPublic = PUBLIC_ROUTES.includes(location.pathname);
      const tokensExist = hasTokens();

      if (!authenticated && !isPublic) {
        if (tokensExist) {
          return;
        }
        throw redirect({ to: "/login" });
      }

      if (authenticated && isPublic && location.pathname !== "/reset-password" && location.pathname !== "/verify-email") {
        throw redirect({ to: "/pair-device" });
      }
    },
  });

  return router;
};
