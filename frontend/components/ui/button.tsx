import { cn } from "@/lib/utils";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "outline";
};

export function Button({ variant = "primary", className, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors",
        variant === "primary" && "bg-cyan text-void hover:bg-cyan/90",
        variant === "outline" && "border border-line text-paper hover:border-cyan/50 hover:text-cyan",
        variant === "ghost" && "text-mist hover:bg-surface-raised hover:text-paper",
        className,
      )}
      {...props}
    />
  );
}
