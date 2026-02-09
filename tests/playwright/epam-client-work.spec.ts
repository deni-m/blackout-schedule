import { test, expect } from '@playwright/test';

// Test: EPAM Client Work visibility
// Scenario Steps:
// 1. Navigate to https://www.epam.com/
// 2. Open "Services" from the header menu
// 3. Click the "Explore Our Client Work" link
// 4. Verify that the text "Client Work" is visible on the page

test('EPAM - Client Work page shows heading', async ({ page }) => {
  await page.goto('https://www.epam.com/');

  // Handle cookie banner if present
  const acceptCookiesSelector = '[aria-label="cookie consent"] button, button#onetrust-accept-btn-handler, button:has-text("Accept")';
  try {
    const cookiesButton = await page.locator(acceptCookiesSelector).first();
    if (await cookiesButton.isVisible()) {
      await cookiesButton.click();
    }
  } catch {}

  // Navigate to Services
  const servicesNav = page.getByRole('navigation').getByRole('link', { name: /services/i }).first();
  await servicesNav.waitFor({ state: 'visible' });
  await servicesNav.click();

  // Click "Explore Our Client Work"
  const exploreLink = page.getByRole('link', { name: /explore our client work/i });
  await exploreLink.waitFor({ state: 'visible' });
  await exploreLink.click();

  // Assert "Client Work" text is visible
  const clientWorkHeading = page.getByRole('heading', { name: /client work/i });
  await expect(clientWorkHeading).toBeVisible();
});