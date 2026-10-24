import { Component, type ErrorInfo, type ReactNode } from "react";
import { Link } from "react-router-dom";
import i18n from "../i18n";
import { handleCrash } from "../lib/sentry";
import { reportCrash, truncateComponentStack } from "../lib/crashReporter";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

// Last line of defense against a render-time crash. This project has hit
// real ones live (unregistered exercise types, etc. -- see CLAUDE.md's
// footguns), and until now a single bad render anywhere under this
// boundary would blank the whole app. Uses the i18next instance directly
// (i18n.t) rather than the useTranslation hook, since class components
// can't use hooks.
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error("Unhandled render error caught by ErrorBoundary:", error, info);
    // ALSO ship it to the feedback collector (console.error alone
    // vanishes when the tab closes). reportCrash dedups by message and
    // can never throw, so this is safe even mid-crash.
    reportCrash("error_boundary", error.message, error.stack, {
      component_stack: truncateComponentStack(info.componentStack),
    });
    // Sentry, if configured and the learner allows it (Never/Ask/Always).
    handleCrash(error, truncateComponentStack(info.componentStack));
  }

  handleReset = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="card" style={{ textAlign: "center", marginTop: 40 }}>
          <div style={{ fontSize: "3rem" }}>⚠️</div>
          <h2>{i18n.t("error_boundary.title")}</h2>
          <p className="muted">{i18n.t("error_boundary.body")}</p>
          <Link className="btn" to="/" onClick={this.handleReset}>
            {i18n.t("error_boundary.back_home")}
          </Link>
        </div>
      );
    }
    return this.props.children;
  }
}
