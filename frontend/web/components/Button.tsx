type ButtonProps = {
  children: React.ReactNode;
  variant?: "primary" | "secondary";
};

export default function Button({
  children,
  variant = "primary",
}: ButtonProps) {
  const base =
    "px-4 py-2 rounded-lg font-medium transition active:scale-95";

  const variants = {
    primary: "bg-green-600 hover:bg-green-700 text-white",
    secondary: "bg-zinc-700 hover:bg-zinc-600 text-white",
  };

  return <button className={`${base} ${variants[variant]}`}>{children}</button>;
}
