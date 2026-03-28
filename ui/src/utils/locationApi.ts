/**
 * Location Manager API URL helpers.
 *
 * Centralizes the URL construction logic previously duplicated across
 * LocationModal, CreateLocationFromTemplateModal, and AddLocationModal.
 */

import { locations_url } from '../store';

/**
 * Get the Location Manager base URL (without the /locations suffix).
 *
 * @throws Error if Location Manager is not available
 */
export function locationBaseUrl(): string {
  const base = locations_url.value;
  if (!base) {
    throw new Error('Location Manager not available');
  }
  return base.replace(/locations\/?$/, '');
}

/**
 * Build a Location Manager API URL for a specific location.
 *
 * @param locationName - The location name (will be URI-encoded)
 * @param endpoint - Optional sub-endpoint (e.g., "set_representation/node_name")
 * @returns The fully constructed URL string
 * @throws Error if Location Manager is not available
 */
export function locationApiUrl(locationName: string, endpoint?: string): string {
  let url = `${locationBaseUrl()}location/${encodeURIComponent(locationName)}`;
  if (endpoint) {
    url += `/${endpoint}`;
  }
  return url;
}
