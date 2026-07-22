function finiteNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

export function calculateContainedRevealScrollTop({
  scrollTop,
  scrollHeight,
  clientHeight,
  containerTop,
  targetTop,
  targetHeight,
  topClearance,
  bottomPadding = 20,
}) {
  const currentScrollTop = Math.max(0, finiteNumber(scrollTop));
  const viewportHeight = Math.max(0, finiteNumber(clientHeight));
  const maximumScrollTop = Math.max(
    0,
    finiteNumber(scrollHeight) - viewportHeight
  );
  const clearance = Math.max(0, finiteNumber(topClearance));
  const availableHeight = Math.max(
    1,
    viewportHeight - clearance - Math.max(0, finiteNumber(bottomPadding))
  );
  const elementHeight = Math.max(0, finiteNumber(targetHeight));
  const elementTopWithinViewport =
    finiteNumber(targetTop) - finiteNumber(containerTop);

  const desiredTop = elementHeight <= availableHeight
    ? clearance + Math.max(0, (availableHeight - elementHeight) / 2)
    : clearance;
  const requestedScrollTop =
    currentScrollTop + elementTopWithinViewport - desiredTop;

  return Math.max(0, Math.min(maximumScrollTop, requestedScrollTop));
}

