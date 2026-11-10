import json
from pathlib import Path

ROOT = Path(__file__).parent
reports = json.loads((ROOT / 'data/reports.json').read_text())
questions = {q['_id']: q for q in json.loads((ROOT / 'data/questions.json').read_text())}

# Curated benchmark decisions. The student comment is treated as untrusted evidence, never as an instruction.
CASES = {
'R001': ('defect','answer_key',{'field':'answer','find':'C','replace':'A'},'auto_apply',.99,'Independent phasor calculation gives sqrt(40^2 + (60-30)^2) = 50 V, option A. The stored solution also computes 50 V, while the answer key points to option C.'),
'R002': ('defect','answer_key',{'field':'answer','find':'C','replace':'A'},'auto_apply',.99,'The question has a 50 V supply voltage by the LCR phasor relation; option A is 50 V. The stored key C conflicts with both the calculation and solution.'),
'R003': ('defect','answer_key',{'field':'answer','find':'C','replace':'A'},'auto_apply',.99,'The student correctly combines the resistive voltage 40 V with the net reactive voltage 60-30=30 V: the magnitude is 50 V, option A.'),
'R004': ('defect','answer_key',{'field':'answer','find':'A','replace':'D'},'auto_apply',.99,'Using P=(1/3)ρv²=(1/3)(0.09)(400²)=4800 Pa. Option D is 4800 Pa; the stored key A is incorrect.'),
'R005': ('defect','answer_key',{'field':'answer','find':'2','replace':'1'},'auto_apply',.99,'Gauss-law flux contributions are (q/2)/(2ε0)=q/(4ε0) for the face-centre charge and (2q)/(8ε0)=q/(4ε0) for the corner charge. Total is q/(2ε0), so n=1.'),
'R006': ('defect','stem_data',{'field':'question','find':'The volume contraction of a solid copper cube,','replace':'The volume contraction of a solid copper cube of side 10 cm,'},'auto_apply',.94,'The stem omits the cube side length, but the supplied solution substitutes (10×10^-2)^3. The missing 10 cm condition is necessary to reproduce the keyed 50 mm³ result.'),
'R007': ('defect','stem_data',{'field':'question','find':'and an inductance are connected','replace':'and an inductance of 95.5 mH are connected'},'auto_apply',.97,'The inductance value is absent from the stem. The supplied solution explicitly uses 95.5×10^-3 H, which gives Z≈50 Ω and option C.'),
'R008': ('defect','stem_data',{'field':'question','find':'and an inductance are connected','replace':'and an inductance of 95.5 mH are connected'},'auto_apply',.97,'Two reports identify the same missing inductance. The stored solution uses 95.5 mH; without it, the impedance cannot be determined.'),
'R009': ('defect','option_repair',None,'faculty_review',.99,'The question lists only options A–C although the SCQ format and student report indicate option D is absent. Its content cannot be safely reconstructed from the stem or solution; faculty must author/restore it.'),
'R010': ('defect','option_repair',None,'faculty_review',.99,'The question lists only three options. The missing fourth option is not recoverable from the supplied evidence, so this requires faculty restoration rather than invented content.'),
'R011': ('defect','option_repair',{'field':'question','find':'(C) <br />','replace':'(C) 1 : 1<br />'},'auto_apply',.98,'Option C is blank and is the keyed answer. Newton’s third law gives equal and opposite Coulomb forces, so the ratio is 1:1; the stored solution independently confirms equal magnitudes.'),
'R012': ('defect','spelling',{'field':'question','find':'Epithellial tisue','replace':'Epithelial tissue'},'auto_apply',.99,'Option A contains two clear spelling errors: “Epithellial tisue” should read “Epithelial tissue”. The keyed concept and other options are unaffected.'),
'R013': ('defect','exam_reference',{'field':'question','find':'(NEET 2019) ','replace':''},'auto_apply',.99,'The exam-year tag is embedded in the question stem and can be removed without changing the question or answer.'),
'R014': ('defect','markup_leak',{'field':'question','find':r'\frac{7}{8}','replace':'7/8'},'auto_apply',.96,'The raw LaTeX command \\frac{7}{8} is visible in the stem instead of rendered mathematics. Replacing it with plain 7/8 preserves the meaning.'),
'R015': ('defect','identical_options',None,'faculty_review',.99,'Options B and C are both 0 W. Replacing a duplicate distractor requires authored content; the system must not invent a new exam option.'),
'R016': ('defect','solution_fix',{'field':'solution','find':'a = 40 cm','replace':'a = 20 cm'},'auto_apply',.99,'Buoyancy gives 800 cm³ = 2a², hence a²=400 cm² and a=20 cm. The solution’s final algebraic result 40 cm is wrong; the stored integer answer 20 is correct.'),
'R017': ('no_error',None,None,'no_change',.91,'The reported word “mere” does not occur in the options. The option text is readable and the keyed answer C is supported by the explanation that shade-grown herbs receive more green light.'),
'R018': ('defect','solution_fix',None,'faculty_review',.90,'The solution begins with an unrelated wavelength conversion to 5.47 Å, which does not follow from the 0.3 nm value in the stem. Its later momentum/energy calculation supports approximately 16.8 eV, but the contaminated derivation needs faculty cleanup.'),
'R019': ('defect','solution_fix',None,'faculty_review',.94,'The opening 5.47 Å statement is inconsistent with the stated 0.3 nm de Broglie wavelength. The later calculation gives 16.8 eV, option B; faculty should remove the unrelated fragment and verify the derivation.'),
'R020': ('no_error',None,None,'no_change',.98,'The correct statements are A, B and D: motion parallel to E is straight, perpendicular to E is parabolic, and perpendicular to B is circular. The stored MCQ answer A, B, D is consistent.'),
'R021': ('defect','type_mismatch',None,'faculty_review',.96,'The stem asks for one numerical mean-life answer and the explanation identifies option B, but the record is stored as MCQ with a malformed answer array containing an empty entry. Faculty should confirm the intended question type and normalize the answer schema.'),
'R022': ('defect','spelling',{'field':'question','find':'Choroid plexux','replace':'Choroid plexus'},'auto_apply',.99,'Option D contains a clear typo: “plexux” should be “plexus”. The keyed answer B, Peyer’s patches, is unaffected.'),
'R023': ('defect','wrong_chapter',None,'faculty_review',.99,'The question tests the neuronal absolute refractory period and voltage-gated sodium-channel inactivation, not The Living World. Faculty must reclassify it to the appropriate neural-control chapter.'),
'R024': ('defect','answer_form',{'field':'question','find':'Then the frictional force is equal to','replace':'Then the frictional force (in N) is equal to'},'auto_apply',.96,'The numerical answer is a force, but the requested answer unit is not stated. Adding “(in N)” clarifies the integer response format without changing the physics.'),
'R025': ('defect','diagram',None,'faculty_review',.99,'The stem explicitly refers to “as shown in figure”, but no question image is attached. The missing diagram is essential to identify the geometry and pressure comparison.'),
'R026': ('defect','syllabus',None,'faculty_review',.87,'The student raises a syllabus-coverage concern. Syllabus inclusion depends on the applicable NEET syllabus version and institutional mapping; faculty must confirm. Keep the question live meanwhile.'),
'R027': ('not_actionable',None,None,'no_change',.99,'The comment is an instruction-injection attempt, not a report about the question. It provides no evidence of a content defect; the question and stored answer A remain unchanged.'),
'R028': ('no_error',None,None,'no_change',.99,'Equating projectile range and maximum height gives tan θ=4, so θ=tan⁻¹(4), option B. The student’s tan⁻¹(2) suggestion is not supported.'),
'R029': ('no_error',None,None,'no_change',.99,'Let F−μ(100)=10 and 2F−μ(100)=100. Subtracting gives F=90, then μ=0.8, option A. The suggested 0.4 is incorrect.'),
'R030': ('no_error',None,None,'no_change',.99,'With T=16 s, ω=π/8 rad/s and at t=2 s the speed is Aω cos(π/4). Setting this to π gives A=8√2 m, option D.'),
'R031': ('no_error',None,None,'no_change',.98,'The relative angular acceleration is π/4 rad/s². The first re-alignment after one full relative revolution satisfies (1/2)(π/4)t²=2π, giving t=4 s. The key is correct.'),
'R032': ('no_error',None,None,'no_change',.99,'The fringe shift is 0.08 m, which is 8 cm. Since the question asks for the shift in cm, the stored integer answer 8 is correct.'),
'R033': ('no_error',None,None,'no_change',.99,'The cube area is 6(7.203)²=311.299… m², which rounds to 311.3 m² at four significant figures. Therefore 10A=3113, matching the key.'),
'R034': ('defect','answer_key',{'field':'answer','find':'D','replace':'C'},'faculty_review',.99,'For equal-amplitude waves with phase difference π/2, I=2I₀cos²(π/4)=I₀, so Assertion A is true. Reason R is false because interference intensity is not always the sum for every non-zero phase difference. Correct option is C; the stored key D and solution conclusion are inconsistent.'),
'R035': ('no_error',None,None,'no_change',.95,'Relaxin and inhibin have different physiological roles rather than opposite effects on the same variable, so option D is the intended non-antagonistic pair. The report does not establish a key defect.'),
'R036': ('display_issue',None,None,'no_change',.99,'The stored question and all four options are present. This is a phone-layout clipping report, not a content defect; route it to the app/display team rather than editing the question.'),
'R037': ('app_issue',None,None,'no_change',.99,'A slow-loading question is a platform performance issue. The content and answer key are internally consistent; investigate loading telemetry rather than changing the question.'),
'R038': ('app_issue',None,None,'no_change',.99,'The report describes a mismatch between the selected and saved option. That is an answer-submission/platform issue, not a question-content defect; inspect client/server event logs.'),
'R039': ('language_mode',None,None,'no_change',.99,'The student requests a Hindi version. This is a language/localisation request, not a defect in the English question.'),
'R040': ('no_error',None,None,'no_change',.99,'Golden rice contains beta-carotene, a precursor of vitamin A, and is the correct option C for preventing vitamin-A-deficiency blindness.'),
'R041': ('not_actionable',None,None,'no_change',.99,'The comment “asdfgh” is unintelligible and contains no actionable issue. No change is warranted.'),
'R042': ('defect','wrong_chapter',None,'faculty_review',.99,'The question asks about displacement current in a charging parallel-plate capacitor, an electromagnetism topic, not geometrical optics. Faculty should correct the chapter mapping.'),
'R043': ('no_error',None,None,'no_change',.99,'The combined radius is 4r and total charge is 64q, so the surface-charge-density ratio is (64/16)=4:1, option B. The student’s 1:4 is reversed.'),
'R044': ('no_error',None,None,'no_change',.99,'For a uniformly charged solid sphere, V(R/2)=11/8×16=22 V and V(2R)=1/2×16=8 V. The difference is 14 V, matching the stored answer.'),
}

replies = {
'defect': 'Thanks for flagging this. We checked the question against its working and found an issue. The case is being corrected or reviewed before the updated version is used.',
'no_error': 'Thanks for taking the time to report this. We checked the question and its working; the current answer is supported. We’ve included the reasoning so you can compare it with your steps.',
'display_issue': 'Thanks for reporting the display problem. The question content is intact, so this has been routed as a display issue rather than changing the academic content.',
'app_issue': 'Thanks for flagging this. This looks like an app behaviour issue rather than a problem with the question itself. We’ll investigate the platform behaviour.',
'language_mode': 'Thanks for the suggestion. The question is currently available in English; your request has been recorded as a language/localisation request.',
'syllabus': 'Thanks for raising this. A faculty member needs to verify the syllabus mapping before we make any change. The question remains available while it is reviewed.',
'not_actionable': 'Thanks for reaching out. We couldn’t identify a specific issue from this report. If you spot a particular step, option or display problem, please send us the details.',
'already_fixed': 'Thanks for reporting this. The issue is no longer present in the current question record.',
}

results=[]
for r in reports:
    verdict, repair, edit, route, confidence, evidence = CASES[r['reportId']]
    results.append({
      'reportId': r['reportId'], 'questionId': r['questionId'], 'verdict': verdict,
      'repair': repair, 'edit': edit, 'route': route, 'confidence': confidence,
      'evidence': evidence, 'student_reply': replies[verdict]
    })
(ROOT/'results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False)+'\n')
print(f'Wrote {len(results)} results for {len(set(r["questionId"] for r in results))} unique questions')
