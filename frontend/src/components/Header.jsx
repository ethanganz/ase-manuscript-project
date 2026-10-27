import { Bell } from 'lucide-react'

export function Header({ user, unreadCount = 0, onLogin, onLogout }) {
  return (
    <header className="sticky top-0 z-20 border-b border-[#dfe5df] bg-[#fbfcfa]/95 backdrop-blur">
      <div className="mx-auto flex h-[76px] max-w-[1240px] items-center justify-between px-6 lg:px-8">
        <a href="#top" className="flex items-center gap-3" aria-label="Manuscript Explorer home">
          <span className="sr-only">Manuscript Explorer</span>
        </a>

        <nav className="hidden items-center gap-8 text-sm text-[#6e7975] md:flex" aria-label="Primary navigation">
          <a className="font-medium text-[#1e3b35]" href="#collections">Collections</a>
          <a className="transition-colors hover:text-[#1e2a27]" href="#places">Places</a>
          <a className="transition-colors hover:text-[#1e2a27]" href="#about">About</a>
        </nav>

        <div className="flex items-center gap-3">
          {user && unreadCount > 0 && (
            <a
              href="#notifications"
              className="relative rounded-full p-2 text-[#476d5b] transition-colors hover:bg-[#edf1ed]"
              title={`${unreadCount} new ${unreadCount === 1 ? 'notification' : 'notifications'}`}
              aria-label={`${unreadCount} new ${unreadCount === 1 ? 'notification' : 'notifications'}`}
            >
              <Bell className="size-5" />
              <span className="absolute -right-0.5 -top-0.5 flex size-[18px] items-center justify-center rounded-full bg-[#a04a3a] text-[10px] font-semibold text-white">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            </a>
          )}
          {user && (
            <a
              href="#profile"
              className="hidden text-sm text-[#6e7975] transition-colors hover:text-[#1e2a27] sm:inline"
              title="Your profile"
            >
              {user.first_name} {user.last_name}
            </a>
          )}
          <button
            type="button"
            onClick={user ? onLogout : onLogin}
            className="rounded-full border border-[#cbdace] px-4 py-2 text-sm font-medium text-[#476d5b] transition-colors hover:bg-[#edf1ed]"
          >
            {user ? 'Log out' : 'Log in'}
          </button>
        </div>
      </div>
    </header>
  )
}