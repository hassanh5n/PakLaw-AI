import "./globals.css";

export const metadata = {
  title: "PakLaw AI",
  description: "Production web shell for Pakistani legal research"
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

