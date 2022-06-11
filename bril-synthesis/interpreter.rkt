#lang rosette

(define (interpret formula)
  (match formula
    [lit            (constant lit integer?)]))

; This implements a Bril solver.
(define (BRIL formula)
  (solve (assert (eq? (1 interpret formula)))))

(BRIL `(∧ r o (∨ s e (¬ t)) t (¬ e)))