import type { ReactNode } from "react";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  variant?: "default" | "strong" | "subtle";
  hover?: boolean;
  onClick?: () => void;
}

export function GlassCard({
  children,
  className = "",
  variant = "default",
  hover = false,
  onClick,
}: GlassCardProps) {
  const variantClass =
    variant === "strong" ? "glass-strong"
    : variant === "subtle" ? "glass-subtle"
    : "glass";

  return (
    <div
      className={[
        variantClass,
        "rounded-2xl",
        hover ? "hover-lift cursor-pointer" : "",
        onClick ? "cursor-pointer" : "",
        className,
      ].join(" ")}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {children}
    </div>
  );
}
