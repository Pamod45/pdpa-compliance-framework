import React from "react";

export default function Privacy({ meta, user, onAccount }) {
  const days = meta?.retention_days;
  const keep = days === undefined ? "for a limited time" : days > 0 ? `for ${days} days after the run, then deleted automatically` : "until you delete them";
  return (
    <div className="privacy">
      <header className="page-head"><h1>Privacy</h1>
        <p>What PCEF keeps about you, why, for how long, and how to get it or remove it.</p></header>

      <section className="pv-sec">
        <h2>Without an account</h2>
        <p>Nothing about you or your plan is kept. An uploaded SSP is read to score it and then discarded with the run; the result exists only in your browser tab until you close it.</p>
        <p>The browser remembers two settings on this device only: whether you have seen the tour and whether presenter mode is on. They are not sent anywhere.</p>
      </section>

      <section className="pv-sec">
        <h2>With an account</h2>
        <table className="pv-t">
          <thead><tr><th>What</th><th>Why</th><th>How long</th></tr></thead>
          <tbody>
            <tr><td>Your email address</td><td>To sign you in</td><td>Until you delete your account</td></tr>
            <tr><td>Your password, as a one-way argon2 hash</td><td>To check your password; the password itself is never stored</td><td>Until you delete your account</td></tr>
            <tr><td>A sign-in session (a fingerprint of the token in your browser cookie)</td><td>To keep you signed in</td><td>14 days, or until you sign out</td></tr>
            <tr><td>A document you paste into Draft an SSP</td><td>Sent to Google's Gemini API to draft the plan; Google may use it to improve its products and people may review it (free tier)</td><td>Not stored by PCEF; Google's terms apply to what it receives</td></tr>
            <tr><td>Saved runs: the results, including the parts of your plan's text they quote</td><td>So you can reopen, compare and print them</td><td>{keep[0].toUpperCase() + keep.slice(1)}, or until you delete them</td></tr>
          </tbody>
        </table>
        <p>The uploaded SSP file itself is not stored, only the scored result. Data is kept on this site's server and is not shared, sold or used for anything else. The one exception is a document you choose to send to Gemini in Draft an SSP, after confirming. There are no advertising or tracking cookies; the only cookie is the sign-in session.</p>
        <p className="pv-warn">Saved runs quote your plan's implementation text. If your plan contains confidential details, score it without signing in, or delete the run afterwards.</p>
      </section>

      <section className="pv-sec">
        <h2>Your choices</h2>
        <ul>
          <li>Delete any saved run from <b>My runs</b>.</li>
          <li>Download everything stored about you as one JSON file.</li>
          <li>Delete your account, which removes your email, sessions and every saved run at once.</li>
        </ul>
        {user ? <button className="primary" onClick={onAccount}>Go to your account</button>
              : <p className="small">The download and delete options appear on the account page once you are signed in.</p>}
      </section>
    </div>
  );
}
