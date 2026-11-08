const kraWeights = {
  'kra-I': 0.6,
  'kra-II': 0.2,
  'kra-III': 0.1,
  'kra-IV': 0.1,
};

class SetSefResult {
  final double raw;
  final String breakdown;
  SetSefResult(this.raw, this.breakdown);
}

SetSefResult computeSetSef(List<double?> ratings, String type) {
  final filled = ratings.whereType<double>().toList();
  if (filled.isEmpty) return SetSefResult(0, 'No ratings entered');
  final avg = filled.reduce((a, b) => a + b) / filled.length;
  final factor = type == 'SET' ? 0.36 : 0.24;
  final raw = avg * factor;
  return SetSefResult(raw, 'avg ${avg.toStringAsFixed(2)} × $factor = ${raw.toStringAsFixed(2)}');
}

double cap(double sum, double? capVal) {
  if (capVal == null) return sum;
  return sum > capVal ? capVal : sum;
}
