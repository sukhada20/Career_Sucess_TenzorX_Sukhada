import React from 'react';
import { useTheme } from '../context/ThemeContext';

/**
 * Editorial paper backdrop.
 * Two soft warm radial washes + a near-invisible vertical column rule on the right edge
 * of the workspace. The grain itself is painted on body::before in index.css.
 */
const Background3D = () => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <div
      aria-hidden
      style={{
        position: 'fixed',
        top: 0, left: 0,
        width: '100%', height: '100%',
        zIndex: 0,
        pointerEvents: 'none',
        overflow: 'hidden',
      }}
    >
      {/* Warm vignette — top-left */}
      <div style={{
        position: 'absolute',
        width: '70vw', height: '70vw',
        top: '-22vw', left: '-18vw',
        background: isDark
          ? 'radial-gradient(circle, rgba(40, 36, 28, 0.55) 0%, transparent 60%)'
          : 'radial-gradient(circle, rgba(232, 222, 200, 0.55) 0%, transparent 60%)',
        filter: 'blur(30px)',
      }} />

      {/* Cool subtle wash — bottom-right (navy ink ghost) */}
      <div style={{
        position: 'absolute',
        width: '60vw', height: '60vw',
        bottom: '-22vw', right: '-15vw',
        background: isDark
          ? 'radial-gradient(circle, rgba(30, 86, 199, 0.04) 0%, transparent 65%)'
          : 'radial-gradient(circle, rgba(27, 44, 94, 0.05) 0%, transparent 65%)',
        filter: 'blur(40px)',
      }} />

      {/* Hairline editorial column rule at 78vw — only on wide screens */}
      <div style={{
        position: 'absolute',
        top: '0',
        right: '22%',
        bottom: '0',
        width: '1px',
        background: isDark
          ? 'linear-gradient(180deg, transparent 0%, rgba(236, 230, 215, 0.05) 18%, rgba(236, 230, 215, 0.06) 82%, transparent 100%)'
          : 'linear-gradient(180deg, transparent 0%, rgba(23, 27, 39, 0.05) 18%, rgba(23, 27, 39, 0.07) 82%, transparent 100%)',
      }} />
    </div>
  );
};

export default Background3D;
