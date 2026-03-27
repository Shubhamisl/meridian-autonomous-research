/* eslint-disable react-refresh/only-export-components */
import type { ReactElement, ReactNode } from 'react';

import { render, type RenderOptions } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

interface RenderWithProvidersOptions extends Omit<RenderOptions, 'wrapper'> {
  route?: string;
  path?: string;
}

function TestRoutes({
  children,
  path,
  route,
}: {
  children: ReactNode;
  path: string;
  route: string;
}) {
  return (
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path={path} element={children} />
      </Routes>
    </MemoryRouter>
  );
}

export function renderWithProviders(
  ui: ReactElement,
  { route = '/', path = '*', ...renderOptions }: RenderWithProvidersOptions = {},
) {
  return render(ui, {
    wrapper: ({ children }) => <TestRoutes path={path} route={route}>{children}</TestRoutes>,
    ...renderOptions,
  });
}
