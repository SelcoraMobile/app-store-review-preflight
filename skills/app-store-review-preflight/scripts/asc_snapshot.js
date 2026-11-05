/*
 * App Store Connect read-only snapshot for the app-store-review-preflight skill.
 *
 * Where: a browser tab on https://appstoreconnect.apple.com where the user is already
 * signed in (for example through a browser-automation tool's "run JavaScript" action).
 * What: GET requests to the same-origin API that the App Store Connect web UI uses
 * (/iris/v1, /iris/v2). Resource names mirror the public App Store Connect API, but
 * this path is unofficial and may change. App Privacy answers (dataUsages) are only
 * available here, not in the public API.
 *
 * Rules: GET only. Never add POST/PATCH/DELETE here. Never type credentials. The
 * snapshot returns no passwords (demo account: presence only) and strips query
 * strings from URLs.
 *
 * Usage (after pasting this file):
 *   const s = await ascSnapshot('1234567890');            // every part
 *   const s = await ascSnapshot('1234567890', ['subscriptions', 'privacy']);
 *   JSON.stringify(s.subscriptions)                       // print one part at a time
 * Parts: app, versions, builds, appInfo, subscriptions, iap, privacy, availability, eula.
 */
(function () {
  const get = async (path, version = 'v1') => {
    const res = await fetch(`/iris/${version}/${path}`, { headers: { accept: 'application/json' }, credentials: 'same-origin' });
    if (!res.ok) return { error: res.status };
    return res.json();
  };
  const strip = (u) => (typeof u === 'string' ? u.replace(/\?.*$/, '') : u);
  const LIVE = /READY_FOR_SALE|READY_FOR_DISTRIBUTION|REPLACED_WITH_NEW_VERSION|REMOVED_FROM_SALE/;

  const parts = {
    async app(appId) {
      const a = await get(`apps/${appId}`);
      if (a.error) return a;
      const x = a.data.attributes;
      return { name: x.name, bundleId: x.bundleId, sku: x.sku, primaryLocale: x.primaryLocale, contentRightsDeclaration: x.contentRightsDeclaration };
    },

    async versions(appId) {
      const vs = await get(`apps/${appId}/appStoreVersions?filter[platform]=IOS&limit=10`);
      if (vs.error) return vs;
      const list = vs.data.map((v) => ({ id: v.id, version: v.attributes.versionString, state: v.attributes.appStoreState || v.attributes.appVersionState, releaseType: v.attributes.releaseType, created: v.attributes.createdDate }));
      const editable = vs.data.find((v) => !LIVE.test(v.attributes.appStoreState || v.attributes.appVersionState || ''));
      const out = { list, editable: null };
      if (!editable) return out;
      const b = await get(`appStoreVersions/${editable.id}/build`);
      const rd = await get(`appStoreVersions/${editable.id}/appStoreReviewDetail`);
      const loc = await get(`appStoreVersions/${editable.id}/appStoreVersionLocalizations?limit=50`);
      const r = rd.data ? rd.data.attributes : null;
      out.editable = {
        id: editable.id,
        version: editable.attributes.versionString,
        attachedBuild: b.data ? { build: b.data.attributes.version, state: b.data.attributes.processingState, uploaded: b.data.attributes.uploadedDate } : null,
        review: r ? {
          demoAccountRequired: r.demoAccountRequired, demoAccountNameSet: !!r.demoAccountName, demoAccountPasswordSet: !!r.demoAccountPassword,
          contactSet: !!(r.contactEmail && r.contactPhone && r.contactFirstName && r.contactLastName), notes: r.notes || '',
        } : rd,
        localizations: (loc.data || []).map((l) => {
          const x = l.attributes;
          const d = x.description || '';
          return { locale: x.locale, descriptionLength: d.length, descriptionEnd: d.slice(-300), keywords: x.keywords, promotionalText: x.promotionalText, whatsNewLength: (x.whatsNew || '').length, supportUrl: strip(x.supportUrl), marketingUrl: strip(x.marketingUrl) };
        }),
      };
      return out;
    },

    async builds(appId) {
      const bl = await get(`builds?filter[app]=${appId}&sort=-uploadedDate&limit=10&include=preReleaseVersion`);
      if (bl.error) return bl;
      const pre = {};
      (bl.included || []).forEach((i) => { pre[i.id] = i.attributes.version; });
      return bl.data.map((b) => ({ version: pre[b.relationships?.preReleaseVersion?.data?.id], build: b.attributes.version, state: b.attributes.processingState, uploaded: b.attributes.uploadedDate, expired: b.attributes.expired, usesNonExemptEncryption: b.attributes.usesNonExemptEncryption }));
    },

    async appInfo(appId) {
      const ai = await get(`apps/${appId}/appInfos`);
      if (ai.error) return ai;
      const out = [];
      for (const info of ai.data) {
        const il = await get(`appInfos/${info.id}/appInfoLocalizations?limit=50`);
        const ar = await get(`appInfos/${info.id}/ageRatingDeclaration`);
        const cat = await get(`appInfos/${info.id}/primaryCategory`);
        out.push({
          id: info.id, state: info.attributes.appStoreState || info.attributes.state, ageRating: info.attributes.appStoreAgeRating,
          primaryCategory: cat.data ? cat.data.id : null,
          localizations: (il.data || []).map((l) => ({ locale: l.attributes.locale, name: l.attributes.name, subtitle: l.attributes.subtitle, privacyPolicyUrl: strip(l.attributes.privacyPolicyUrl), privacyChoicesUrlSet: !!l.attributes.privacyChoicesUrl })),
          ageRatingDeclaration: ar.data ? ar.data.attributes : ar,
        });
      }
      return out;
    },

    async subscriptions(appId) {
      const sg = await get(`apps/${appId}/subscriptionGroups?limit=20&include=subscriptions`);
      if (sg.error) return sg;
      const subs = (sg.included || []).filter((i) => i.type === 'subscriptions');
      const out = { groups: sg.data.map((g) => g.attributes.referenceName), subscriptions: [] };
      for (const s of subs) {
        const loc = await get(`subscriptions/${s.id}/subscriptionLocalizations?limit=50`);
        const prices = await get(`subscriptions/${s.id}/prices?limit=1`);
        const shot = await get(`subscriptions/${s.id}/appStoreReviewScreenshot`);
        const intro = await get(`subscriptions/${s.id}/introductoryOffers?limit=50`);
        const modes = [...new Set((intro.data || []).map((o) => `${o.attributes.offerMode}/${o.attributes.duration}`))];
        out.subscriptions.push({
          productId: s.attributes.productId, state: s.attributes.state, period: s.attributes.subscriptionPeriod, groupLevel: s.attributes.groupLevel, familySharable: s.attributes.familySharable,
          localizations: (loc.data || []).map((l) => l.attributes.locale), hasPrice: !!(prices.data && prices.data.length), reviewScreenshot: !!shot.data, reviewNoteSet: !!s.attributes.reviewNote, introductoryOffers: modes,
        });
      }
      return out;
    },

    async iap(appId) {
      const r = await get(`apps/${appId}/inAppPurchasesV2?limit=200`);
      if (r.error) return r;
      return r.data.map((p) => ({ productId: p.attributes.productId, type: p.attributes.inAppPurchaseType, state: p.attributes.state }));
    },

    async privacy(appId) {
      const du = await get(`apps/${appId}/dataUsages?include=category,grouping,purpose,dataProtection&limit=500`);
      const pub = await get(`apps/${appId}/dataUsagePublishState`);
      if (du.error) return { error: du.error, publish: pub.data ? pub.data.attributes : pub };
      const rows = du.data.map((d) => {
        const r = d.relationships || {};
        const id = (k) => (r[k] && r[k].data ? r[k].data.id : null);
        return { category: id('category'), purpose: id('purpose'), protection: id('dataProtection') };
      });
      return { rows, publish: pub.data ? pub.data.attributes : pub };
    },

    async availability(appId) {
      let av = await get(`apps/${appId}/appAvailabilityV2`);
      if (av.error) av = await get(`appAvailabilities/${appId}`, 'v2');
      if (av.error || !av.data) return av;
      const out = { availableInNewTerritories: av.data.attributes.availableInNewTerritories, available: [], unavailable: [] };
      const t = await get(`appAvailabilities/${av.data.id}/territoryAvailabilities?limit=200&include=territory`, 'v2');
      (t.data || []).forEach((row) => {
        const terr = row.relationships?.territory?.data?.id;
        (row.attributes.available ? out.available : out.unavailable).push(terr);
      });
      return out;
    },

    async eula(appId) {
      const e = await get(`apps/${appId}/endUserLicenseAgreement`);
      if (e.error) return { customEula: false, status: e.error };
      const text = e.data ? (e.data.attributes.agreementText || '') : '';
      return { customEula: !!text, length: text.length, textStart: text.slice(0, 300) };
    },
  };

  window.ascSnapshot = async function (appId, wanted) {
    if (!/^\d{6,12}$/.test(String(appId))) throw new Error('appId must be the numeric Apple ID of the app');
    const names = wanted && wanted.length ? wanted : Object.keys(parts);
    const result = { appId: String(appId), takenAt: new Date().toISOString() };
    for (const name of names) {
      if (!parts[name]) { result[name] = { error: 'unknown part' }; continue; }
      try { result[name] = await parts[name](appId); } catch (err) { result[name] = { error: String(err) }; }
    }
    return result;
  };
  return 'ascSnapshot ready';
})();
