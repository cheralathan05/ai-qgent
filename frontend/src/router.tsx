import { QueryClient } from "@tanstack/react-query";
import { createRouter, redirect } from "@tanstack/react-router";
import { routeTree } from "./routeTree.gen";
import { entStore } from "./lib/apa/enterprise";

const PUBLIC_ROUTES = ["/login", "/register", "/forgot-password"];

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
      if (!authenticated && !isPublic) {
        throw redirect({ to: "/login" });
      }
    },
  });

  return router;
};
