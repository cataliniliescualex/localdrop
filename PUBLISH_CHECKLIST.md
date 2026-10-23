# Checklist before clicking Public / Publish release

- [ ] Confirm copyright/provenance and the right to release all source and artwork under MPL-2.0.
- [ ] Confirm the name WarpCoil does not create a conflicting trademark risk.
- [ ] Review security/privacy documentation and update the private vulnerability reporting route.
- [ ] Test a clean download and launch on Windows and Ubuntu; test Safari upload from an iPhone.
- [ ] Run `python3 -m unittest -v test_localdrop.py`.
- [ ] Ensure there are no secrets, private addresses, recordings, tokens or large local files in the repository.
- [ ] Publish with release tag `v1.3.1` and attach the ZIP from the package.
- [ ] Clearly label the release **Public Beta**, and warn users to use trusted local networks only.
