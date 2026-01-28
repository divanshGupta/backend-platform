import Button from "@/components/Button";

export default function Home() {
  return (
    <div className="min-h-screen flex items-center justify-center gap-4">
      <Button>Start Workout</Button>
      <Button variant="secondary">Skip</Button>
    </div>
  );
}
