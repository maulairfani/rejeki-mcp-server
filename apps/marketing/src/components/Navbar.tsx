import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { LogoMark } from "./LogoMark"

export function Navbar() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  const close = () => setOpen(false)

  return (
    <nav className="nav">
      <div className="container">
        <div className="nav-inner">
          <Link
            to="/"
            className="nav-logo"
            onClick={(e) => {
              e.preventDefault()
              navigate("/")
              window.scrollTo({ top: 0, behavior: "smooth" })
              close()
            }}
          >
            <LogoMark size={28} />
            <span>Envel</span>
          </Link>

          <div className="nav-links">
            <div className="dropdown-trigger">
              <button className="btn btn-ghost" style={{ fontSize: 14, fontWeight: 600 }}>
                What is Envel? <span className="chevron">▾</span>
              </button>
              <div className="dropdown">
                <a href="/#method">The Method</a>
                <a href="/#features">Features</a>
                <a
                  href="/docs"
                  onClick={(e) => {
                    e.preventDefault()
                    navigate("/docs")
                  }}
                >
                  Docs
                </a>
              </div>
            </div>
            <div className="dropdown-trigger">
              <button className="btn btn-ghost" style={{ fontSize: 14, fontWeight: 600 }}>
                Learn <span className="chevron">▾</span>
              </button>
              <div className="dropdown">
                <a
                  href="/blog"
                  onClick={(e) => {
                    e.preventDefault()
                    navigate("/blog")
                  }}
                >
                  Blog
                </a>
                <a href="#">Tips & Guides</a>
                <a href="#">Product Updates</a>
              </div>
            </div>
          </div>

          <button
            className="btn btn-primary nav-cta"
            onClick={() => {
              window.location.href = "https://platform.envel.dev/signup"
            }}
          >
            Get Started
          </button>

          <button
            className="nav-burger"
            aria-label="Toggle menu"
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            <span className={`burger-bar ${open ? "open" : ""}`} />
            <span className={`burger-bar ${open ? "open" : ""}`} />
            <span className={`burger-bar ${open ? "open" : ""}`} />
          </button>
        </div>

        <div className={`nav-mobile ${open ? "open" : ""}`}>
          <div className="nav-mobile-section">
            <div className="nav-mobile-label">What is Envel?</div>
            <a href="/#method" onClick={close}>The Method</a>
            <a href="/#features" onClick={close}>Features</a>
            <a
              href="/docs"
              onClick={(e) => {
                e.preventDefault()
                navigate("/docs")
                close()
              }}
            >
              Docs
            </a>
          </div>
          <div className="nav-mobile-section">
            <div className="nav-mobile-label">Learn</div>
            <a
              href="/blog"
              onClick={(e) => {
                e.preventDefault()
                navigate("/blog")
                close()
              }}
            >
              Blog
            </a>
            <a href="#" onClick={close}>Tips & Guides</a>
            <a href="#" onClick={close}>Product Updates</a>
          </div>
          <button
            className="btn btn-primary btn-lg"
            style={{ width: "100%", marginTop: 8 }}
            onClick={() => {
              window.location.href = "https://platform.envel.dev/signup"
            }}
          >
            Get Started
          </button>
        </div>
      </div>
    </nav>
  )
}
