import '@testing-library/jest-dom/vitest';

import { createElement, type ReactNode } from 'react';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

vi.mock('framer-motion', () => {
  const motionFactory = (tag: string) => {
    return function MotionComponent({
      children,
      ...props
    }: {
      children?: ReactNode;
    } & Record<string, unknown>) {
      return createElement(tag, props, children);
    };
  };

  return {
    motion: new Proxy(
      {},
      {
        get: (_target, tag) => motionFactory(String(tag)),
      },
    ),
  };
});
