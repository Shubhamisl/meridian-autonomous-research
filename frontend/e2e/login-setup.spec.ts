import { expect, test } from '@playwright/test';

test('shows Firebase setup guidance when the frontend is unconfigured', async ({ page }) => {
  await page.goto('/login');

  await expect(page.getByRole('heading', { name: /finish workspace setup/i })).toBeVisible();
  await expect(page.getByRole('button', { name: /google sign-in needs setup/i })).toBeDisabled();
  await expect(page.getByText(/firebase sign-in is not configured yet/i)).toBeVisible();
  await expect(page.getByText(/frontend\/\.env\.example/i)).toBeVisible();
});
