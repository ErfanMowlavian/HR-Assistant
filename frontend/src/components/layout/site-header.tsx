import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="border-b">
      <div className="container flex h-14 max-w-3xl items-center justify-between">
        <Link href="/" className="font-bold">
          دستیار استخدام
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <Link href="/" className="text-muted-foreground hover:text-foreground">
            داشبورد منابع انسانی
          </Link>
          <Link href="/apply" className="text-muted-foreground hover:text-foreground">
            ارسال رزومه
          </Link>
        </nav>
      </div>
    </header>
  );
}
