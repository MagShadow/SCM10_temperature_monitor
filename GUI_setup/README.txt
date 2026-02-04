 Scientific Instruments Model SCM10 Graphical User 
	Interface (GUI) Software

1) Installing the Model SCM10 Graphical User Interface (GUI):

If installer does not automatically begin, run "Setup.exe" from the CD root directory.

Follow the prompts to accept the insallation agreements and choose installation directories.  The GUI, and if necessary, the LabVIEW 8.0 run-time engine and NI-VISA support will be installed.

A Windows Start-menu folder will be created and a shortcut will be placed on the desktop.

-----------------------------------------------------------------------------

2) A folder consisting of the standard sensor curves is provided on this CD for your reference.  You may install any of these sensor curves directly to the user memory block if you acquire a grouped sensor from SI or another supported vendor.

-----------------------------------------------------------------------------

3) A folder consisting of some example LabVIEW VIs is provided on this CD for you if you wish to incorporate the SCM10 into your custom programs.  The communication resource string is comprised of a cluster of parameters that pass a string to the VISA resource.  This may require modification if your program uses a single VISA resource input/output.  Do not delete the sub VI called SCM10_IO_Multi.vi.  This sub VI must be present as it is called in the examples.

-----------------------------------------------------------------------------

4) Please be aware that the SCM10 should be connected and powered on before launching the GUI for the first time.

-----------------------------------------------------------------------------
SCM10 GUI Version 1.0.0 Release Notes

-This is the first authorized release of the SCM10 GUI by Scientific Instruments, Inc.  This GUI provides a useful and user-friendly extension to the front panel interface of the physical instrument.

-Minimum System Requirements
	~ Windows 2000/XP
	~ Pentium 4 CPU or better (2 GB of RAM recommended)
	~ Optical drive (for installation CD)
	~ RS-232 or 10BASE-T ethernet connectivity
	~ 150 MB hard disk space available
	~ Optimized for 1024 X 768 pixel resolution

(C) 2012, Scientific Instruments, Inc.
4400 W. Tiffany Drive
West Palm Beach, FL  33407
Tel. 561.881.8500
www.scientificinstruments.com