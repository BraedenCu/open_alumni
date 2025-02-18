// app/layout.tsx

export const metadata = {
  title: "Alumni Graph Visualization",
  description: "Interactive graph visualization of Yale Alumni",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <main>{children}</main>
      </body>
    </html>
  );
}