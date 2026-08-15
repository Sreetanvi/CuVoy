"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = { name: string; children: ReactNode };

type State = { error: string | null };

export class PanelErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`CuVoy ${this.props.name} panel failed`, error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex h-full w-full items-center justify-center p-6 text-center text-sm text-muted-foreground">
          The {this.props.name} panel hit a problem. The rest of the planner is still available.
        </div>
      );
    }
    return this.props.children;
  }
}
