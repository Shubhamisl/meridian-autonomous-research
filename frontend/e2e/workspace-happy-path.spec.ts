import { expect, test } from '@playwright/test';

const E2E_AUTH_KEY = 'meridian:e2e-auth';

const completedWorkspace = {
  id: 'workspace-123',
  job_id: 'job-123',
  query: 'How are battery supply chains changing?',
  markdown_content: '# Executive summary\nMeridian has completed the synthesis and surfaced the key evidence.',
  domain: 'supply_chain',
  format_label: 'briefing_note',
  pipeline: {
    current_phase: 'evidence_scoring',
    phases: ['ingestion', 'domain_classification', 'evidence_scoring', 'synthesis'],
  },
  evidence: [
    {
      source: 'news_wires',
      title: 'Battery plants expand in response to demand',
      credibility_score: 0.92,
      snippet: 'Reuters and regional reporting show factories scaling output.',
      url: 'https://example.com/battery',
    },
  ],
  explainability: {
    active_sources: ['news_wires', 'government_reports'],
    query_refinements: [
      {
        source: 'domain_classifier',
        raw_query: 'battery supply chains',
        enriched_query: 'battery supply chains, manufacturing capacity, and logistics constraints',
      },
    ],
  },
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript((storageKey) => {
    window.localStorage.setItem(storageKey, '1');
  }, E2E_AUTH_KEY);

  await page.route('**/api/research/job-123', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'job-123',
        status: 'completed',
        query: completedWorkspace.query,
      }),
    });
  });

  await page.route('**/api/research/job-123/report', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(completedWorkspace),
    });
  });
});

test('completed workspace shows report and evidence in the browser', async ({ page }) => {
  await page.goto('/workspace/job-123');

  await expect(page.getByRole('heading', { name: /how are battery supply chains changing\?/i }).first()).toBeVisible();
  await expect(page.getByText('Domain: supply chain')).toBeVisible();
  await expect(page.getByText('Format: briefing note')).toBeVisible();
  await expect(page.getByText('Current phase: Evidence Scoring')).toBeVisible();
  await expect(page.getByText('Synthesis Complete')).toBeVisible();
  await expect(page.getByRole('heading', { name: /executive summary/i })).toBeVisible();
  await expect(page.getByText('Battery plants expand in response to demand')).toBeVisible();
  await expect(page.getByText('Reuters and regional reporting show factories scaling output.')).toBeVisible();
  const explainabilityPanel = page.locator('aside').filter({ hasText: 'Explain This Report' });
  await expect(explainabilityPanel.getByText('news wires')).toBeVisible();
  await expect(explainabilityPanel.getByText('government reports')).toBeVisible();
  await expect(
    page.getByText('battery supply chains, manufacturing capacity, and logistics constraints'),
  ).toBeVisible();
  await expect(page.getByRole('link', { name: /original source/i })).toHaveAttribute(
    'href',
    'https://example.com/battery',
  );
});
