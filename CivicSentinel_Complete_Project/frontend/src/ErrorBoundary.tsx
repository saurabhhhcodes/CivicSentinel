import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("CivicSentinel Dashboard Runtime Error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    localStorage.clear();
    sessionStorage.clear();
    window.location.href = "/";
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: "100vh",
          backgroundColor: "#0b1120",
          color: "#f8fafc",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "24px",
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace"
        }}>
          <div style={{
            background: "#131d33",
            border: "1px solid rgba(255, 51, 102, 0.4)",
            borderRadius: "6px",
            padding: "28px",
            maxWidth: "680px",
            width: "100%",
            boxShadow: "0 10px 30px rgba(0,0,0,0.6)"
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
              <span style={{ fontSize: "20px", color: "#ff3366" }}>⚠</span>
              <h2 style={{ margin: 0, fontSize: "16px", letterSpacing: "1px", color: "#ff3366", textTransform: "uppercase" }}>
                CIVICSENTINEL · RUNTIME RECOVERY INTERCEPTOR
              </h2>
            </div>
            <p style={{ color: "#94a3b8", fontSize: "12px", lineHeight: "1.6", margin: "0 0 16px 0" }}>
              An unhandled UI state exception was captured by the safety interceptor. The core services remain operational.
            </p>
            {this.state.error && (
              <pre style={{
                background: "#080c16",
                border: "1px solid #1e293b",
                borderRadius: "4px",
                padding: "12px",
                color: "#ff7700",
                fontSize: "11px",
                overflowX: "auto",
                whiteSpace: "pre-wrap",
                wordBreak: "break-all",
                marginBottom: "18px"
              }}>
                {this.state.error.toString()}
              </pre>
            )}
            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
              <button
                onClick={this.handleReload}
                style={{
                  background: "#00f0ff",
                  color: "#0b1120",
                  border: "none",
                  borderRadius: "3px",
                  padding: "8px 16px",
                  fontSize: "12px",
                  fontWeight: 700,
                  cursor: "pointer"
                }}
              >
                ↻ RELOAD INTERFACE
              </button>
              <button
                onClick={this.handleReset}
                style={{
                  background: "transparent",
                  color: "#94a3b8",
                  border: "1px solid #334155",
                  borderRadius: "3px",
                  padding: "8px 16px",
                  fontSize: "12px",
                  cursor: "pointer"
                }}
              >
                RESET LOCAL CACHE & RETURN HOME
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
